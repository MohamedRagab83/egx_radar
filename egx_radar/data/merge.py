"""Data merge and orchestration for multi-source OHLCV (Layer 2)."""

import logging
import math
import threading
import time
from typing import Dict, List, Optional, Tuple

import pandas as pd

from egx_radar.config.settings import K, SYMBOLS, DATA_SOURCE_CFG, _data_cfg_lock
from egx_radar.data.fetchers import (
    _fetch_yahoo,
    _fetch_stooq,
    _fetch_av_single,
    _fetch_investing,
    _fetch_twelve_data,
)
from egx_radar.data.source_scoring import (
    rank_sources,
    cache_best_source,
    QUALITY_THRESHOLD,
    FALLBACK_THRESHOLD,
)

log = logging.getLogger(__name__)


# ── Cross-Source Agreement Check ───────────────────────────────────────────

def _cross_source_agreement(
    sym: str,
    candidates: list,          # list of (df, label) tuples
    threshold: float = None,
) -> tuple:
    """Return (agreement_score_0_to_1, spread_pct, details_str).

    Computes the percentage spread between the highest and lowest
    last-close price across all available sources.

    spread = (max_close - min_close) / median_close

    If spread > threshold, data sources disagree — flag it.
    threshold default: K.DG_CROSS_SOURCE_SPREAD_LIMIT (e.g. 0.05 = 5%)
    """
    if threshold is None:
        threshold = K.DG_CROSS_SOURCE_SPREAD_LIMIT  # add to settings: default 0.05

    closes = []
    labels = []
    for df_, lbl in candidates:
        try:
            v = float(df_["Close"].iloc[-1])
            if math.isfinite(v) and v > 0:
                closes.append(v)
                labels.append(lbl)
        except (IndexError, ValueError, TypeError):
            continue

    if len(closes) < 2:
        return 1.0, 0.0, "only one source — cannot cross-check"

    min_c = min(closes)
    max_c = max(closes)
    median_c = sorted(closes)[len(closes) // 2]
    spread = (max_c - min_c) / (median_c + 1e-9)

    src_str = ", ".join(f"{lbl}={c:.2f}" for lbl, c in zip(labels, closes))

    if spread <= threshold:
        return 1.0, spread, f"sources agree ({src_str}) spread={spread:.1%}"
    else:
        score = max(0.0, 1.0 - spread / (threshold * 4))
        details = f"PRICE DISAGREEMENT ({src_str}) spread={spread:.1%} > {threshold:.0%}"
        log.warning("Cross-source %s: %s", sym, details)
        return score, spread, details

_source_labels: Dict[str, str] = {}
_source_labels_lock = threading.Lock()


def _merge_ohlcv(
    sym: str,
    sources: List[Tuple[Optional[pd.DataFrame], str]],
    inv_price: Optional[float] = None,
) -> Tuple[Optional[pd.DataFrame], str]:
    """Select best available OHLCV source with priority-ordered candidates.

    Args:
        sym:        Internal symbol name (e.g. "COMI").
        sources:    List of (DataFrame_or_None, source_label) in priority order.
                    Priority is determined by position: first = highest priority.
        inv_price:  Optional Investing.com spot price for cross-check.

    Returns:
        (merged_df, source_label_string) or (None, "—").
    """
    # Ensure Volume column exists on every non-None source
    for df_, label in sources:
        if df_ is not None and "Volume" not in df_.columns:
            df_.loc[:, "Volume"] = 0.0

    candidates: List[Tuple[pd.DataFrame, str]] = []
    for df_, lbl in sources:
        if df_ is None or "Close" not in df_.columns:
            continue
        thresh = K.MIN_BARS if lbl == "Yahoo" else K.MIN_BARS_RELAXED
        if len(df_) >= thresh and df_["Close"].notna().sum() >= thresh:
            last10 = df_["Close"].dropna().iloc[-10:]
            if len(last10) >= 10 and last10.nunique() <= 1 and df_["Volume"].iloc[-5:].sum() == 0:
                log.debug("%s source %s has stale/frozen OHLC — ignoring", sym, lbl)
                continue
            candidates.append((df_, lbl))

    if not candidates:
        return None, "—"

    # ── Adaptive source selection (replaces fixed priority) ────────────
    ranked = rank_sources(candidates, sym)
    best_df, best_label, best_score = ranked[0]

    if best_score["total"] < QUALITY_THRESHOLD:
        log.warning(
            "_merge_ohlcv %s: best source %s quality=%.2f < threshold %.2f — discarding",
            sym, best_label, best_score["total"], QUALITY_THRESHOLD,
        )
        return None, "—"

    fallback_reason = ""
    if best_score["total"] < FALLBACK_THRESHOLD:
        fallback_reason = f"low quality ({best_score['total']:.2f})"
        log.warning(
            "_merge_ohlcv %s: %s quality=%.2f — fallback active",
            sym, best_label, best_score["total"],
        )

    # Re-order candidates by score for downstream consensus close
    candidates = [(df, lbl) for df, lbl, _ in ranked]
    base_df, base_src = candidates[0]

    cache_best_source(sym, base_src)

    log.debug(
        "_merge_ohlcv %s: adaptive → %s (score=%.2f%s) | %s",
        sym, base_src, best_score["total"],
        f" FALLBACK: {fallback_reason}" if fallback_reason else "",
        " > ".join(f"{lbl}={sc['total']:.2f}" for _, lbl, sc in ranked),
    )

    # Drop rows where Close is NaN to prevent propagation
    base_df = base_df.copy()
    base_df = base_df.dropna(subset=["Close"])
    if len(base_df) < K.MIN_BARS_RELAXED:
        log.warning("_merge_ohlcv %s: too few valid Close rows after NaN drop", sym)
        return None, "—"

    # Consensus close: trimmed mean within 5%
    closes = []
    for c_df, _ in candidates:
        try:
            v = float(c_df["Close"].iloc[-1])
            if math.isfinite(v) and v > 0:
                closes.append(v)
        except (IndexError, ValueError, TypeError):
            pass

    if len(closes) >= 2:
        mean_c   = sum(closes) / len(closes)
        filtered = [v for v in closes if abs(v - mean_c) / (mean_c + 1e-9) < 0.05]
        if filtered:
            consensus = sum(filtered) / len(filtered)
            base_df = base_df.copy()
            try:
                base_df.iloc[-1, base_df.columns.get_loc("Close")] = consensus
                base_src += "+" + "+".join(c[1] for c in candidates[1:])
            except (KeyError, IndexError):
                pass

    # Investing.com cross-check
    if inv_price and inv_price > 0:
        try:
            last = float(base_df["Close"].iloc[-1])
            if math.isfinite(last) and abs(last - inv_price) / (last + 1e-9) > 0.03:
                log.warning("Price mismatch %s: base=%.2f INV=%.2f", sym, last, inv_price)
                base_src += "⚠️"
            else:
                base_src += "+INV"
        except (IndexError, ValueError, TypeError):
            pass

    # Cross-source agreement check (Yahoo vs Stooq vs TD)
    if len(candidates) >= 2:
        cs_score, cs_spread, cs_detail = _cross_source_agreement(sym, candidates)
        if cs_spread > K.DG_CROSS_SOURCE_SPREAD_LIMIT:
            # Append disagreement warning to source label so UI shows it
            base_src += f" ⚠️DISAGREE({cs_spread:.0%})"

    # Final sanity check: last Close must be a valid positive number
    try:
        last_close = float(base_df["Close"].iloc[-1])
        if math.isnan(last_close) or not math.isfinite(last_close) or last_close <= 0:
            log.warning("_merge_ohlcv %s: invalid final Close=%.4f — discarding", sym, last_close)
            return None, "—"
    except (IndexError, ValueError, TypeError) as exc:
        log.warning("_merge_ohlcv %s: Close extraction failed: %s", sym, exc)
        return None, "—"

    return base_df, base_src


def download_all() -> Dict[str, pd.DataFrame]:
    """Download OHLCV from all enabled sources and return merged results."""
    global _source_labels
    with _source_labels_lock:
        _source_labels = {}

    sym_list = list(SYMBOLS.keys())
    with _data_cfg_lock:
        cfg = dict(DATA_SOURCE_CFG)

    yahoo_by_sym: Dict[str, pd.DataFrame] = {}
    stooq_by_sym: Dict[str, pd.DataFrame] = {}
    inv_prices: Dict[str, float] = {}
    td_by_sym: Dict[str, pd.DataFrame] = {}

    def _do_yahoo():
        nonlocal yahoo_by_sym
        if cfg.get("use_yahoo"):
            yfin_syms = list(SYMBOLS.values())
            if K.EGX30_SYMBOL not in yfin_syms:
                yfin_syms.append(K.EGX30_SYMBOL)
            log.info("Yahoo Finance: downloading %d symbols...", len(yfin_syms))
            raw = _fetch_yahoo(yfin_syms)
            yahoo_by_sym = {k.replace(".CA", ""): v for k, v in raw.items()}

    def _do_stooq():
        nonlocal stooq_by_sym
        if cfg.get("use_stooq"):
            log.info("Stooq: downloading...")
            stooq_by_sym = _fetch_stooq(sym_list)

    def _do_investing():
        nonlocal inv_prices
        if cfg.get("use_investing"):
            log.info("Investing.com: cross-checking prices...")
            inv_prices = _fetch_investing(sym_list)

    def _do_td():
        nonlocal td_by_sym
        td_key = str(cfg.get("twelve_data_key", "")).strip()
        if cfg.get("use_twelve_data") and td_key:
            log.info("TwelveData: downloading %d symbols...", len(sym_list))
            td_by_sym = _fetch_twelve_data(sym_list, td_key)

    av_by_sym: Dict[str, pd.DataFrame] = {}
    _av_lock = threading.Lock()  # always created; guards av_by_sym writes from _av_bg
    av_thread: Optional[threading.Thread] = None
    av_key = str(cfg.get("alpha_vantage_key", "")).strip()
    if cfg["use_alpha_vantage"] and av_key:
        def _av_bg():
            for s in sym_list[:5]:
                df = _fetch_av_single(s, av_key)
                if df is not None:
                    with _av_lock:   # FIX: guard dict writes from background thread
                        av_by_sym[s] = df
                time.sleep(12)
        av_thread = threading.Thread(target=_av_bg, daemon=True)
        av_thread.start()

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as executor:
        f1 = executor.submit(_do_yahoo)
        f2 = executor.submit(_do_stooq)
        f3 = executor.submit(_do_investing)
        f4 = executor.submit(_do_td)
        f1.result(); f2.result(); f3.result(); f4.result()

    if av_thread is not None and av_thread.is_alive():
        av_thread.join(timeout=5)

    merged: Dict[str, pd.DataFrame] = {}
    local_labels: Dict[str, str]    = {}

    # Parallelize _merge_ohlcv calls across symbols
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _merge_one(sym):
        df_y  = yahoo_by_sym.get(sym)
        df_s  = stooq_by_sym.get(sym)
        with _av_lock:
            df_a = av_by_sym.get(sym)
        df_t  = td_by_sym.get(sym)
        inv_p = inv_prices.get(sym)

        source_list: List[Tuple[Optional[pd.DataFrame], str]] = [
            (df_y, "Yahoo"),
            (df_s, "Stooq"),
            (df_t, "TD"),
            (df_a, "AV"),
        ]
        return sym, _merge_ohlcv(sym, source_list, inv_price=inv_p)

    max_workers = min(K.SCAN_MAX_WORKERS, len(sym_list))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_merge_one, sym): sym for sym in sym_list}
        for future in as_completed(futures):
            try:
                sym, (df_final, label) = future.result()
                if df_final is not None:
                    if "Volume" not in df_final.columns:
                        df_final = df_final.copy()
                        df_final["Volume"] = 0.0
                    merged[SYMBOLS[sym]] = df_final
                    local_labels[sym] = label
            except Exception as exc:
                sym = futures[future]
                log.warning("merge failed for %s: %s", sym, exc)

    # Add EGX30 Proxy to merged results if available from Yahoo
    egx_proxy_sym = K.EGX30_SYMBOL.replace(".CA", "") # It shouldn't have .CA, but just in case
    if egx_proxy_sym in yahoo_by_sym:
        df_proxy = yahoo_by_sym[egx_proxy_sym]
        if df_proxy is not None and len(df_proxy) >= K.EGX30_HEALTH_BARS:
            if "Volume" not in df_proxy.columns:
                df_proxy = df_proxy.copy()
                df_proxy["Volume"] = 0.0
            merged[K.EGX30_SYMBOL] = df_proxy
            local_labels["EGX30"] = "Yahoo"

    with _source_labels_lock:
        _source_labels = local_labels

    log.info(
        "Merged: %d symbols | Y:%d S:%d AV:%d INV:%d TD:%d",
        len(merged), len(yahoo_by_sym), len(stooq_by_sym),
        len(av_by_sym), len(inv_prices), len(td_by_sym),
    )
    return merged


__all__ = [
    "_merge_ohlcv",
    "download_all",
    "_source_labels",
    "_source_labels_lock",
]
