"""
main.py — EGX Radar Pro
=========================
Rebuild-edge pipeline:
1) Diagnose why legacy loses
2) Build and optimize Smart Rank 2.0
3) Validate old vs new with strict improvement gates
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import SYMBOLS
from core.market_regime import detect_market_regime
from core.signal_engine import evaluate_snapshot, format_signal_log, generate_trade_signal
from backtest.metrics import print_metrics
from backtest.validator import diagnose_failure, validate_old_vs_new
from data.loader import load_market_data
from utils.logger import get_logger

log = get_logger("egx_radar_pro")


def signal_preview(market_data: Dict[str, pd.DataFrame], top_n: int = 5) -> None:
    latest = min(df.index.max() for df in market_data.values() if not df.empty)
    snaps = []
    for sym, df in market_data.items():
        if latest not in df.index:
            continue
        snap = evaluate_snapshot(df[df.index <= latest].tail(260), sym)
        if snap is not None:
            snaps.append(snap)

    regime = detect_market_regime(snaps)
    print(f"\n{'═' * 60}")
    print("  SMART RANK 2.0 PREVIEW")
    print(f"  Date: {latest.strftime('%Y-%m-%d')}   Regime: {regime}")
    print(f"{'═' * 60}")

    shown = 0
    for snap in sorted(snaps, key=lambda s: s.smart_rank_v2, reverse=True):
        sig = generate_trade_signal(snap, regime, [], strategy="v2")
        decision = sig[0] if sig else "WAIT"
        print(format_signal_log(snap, decision))
        print()
        shown += 1
        if shown >= top_n:
            break


def _print_diagnosis(diag: Dict) -> None:
    print(f"\n{'═' * 60}")
    print("  PHASE 1 — DIAGNOSIS")
    print(f"{'═' * 60}")
    print_metrics("legacy metrics", diag["legacy_metrics"])
    print("\n  Exit mix:", diag["legacy_exit_mix"])
    eq = diag["entry_quality"]
    print("\n  Entry quality leakage:")
    print(f"    trend fail %              : {eq['trend_fail_pct']}")
    print(f"    RSI outside 45-65 %       : {eq['rsi_outside_45_65_pct']}")
    print(f"    volume <= 1.2 %           : {eq['volume_ratio_le_1_2_pct']}")
    print(f"    ATR% > 3% %               : {eq['atr_pct_gt_3_pct']}")
    print("\n  SmartRank bucket quality:")
    for row in diag["legacy_smart_rank_buckets"]:
        print(f"    SR {row['bucket']}: n={row['count']} WR={row['winrate_pct']} Exp={row['expectancy_pct']}")


def _print_comparison(comp: Dict) -> None:
    print(f"\n{'═' * 60}")
    print("  PHASE 6 — OLD VS NEW VALIDATION")
    print(f"{'═' * 60}")
    print_metrics("old system", comp["old"])
    print_metrics("new system (smart rank 2.0)", comp["new"])

    print("\n  Optimized parameters:")
    for k, v in comp["new_params"].items():
        print(f"    {k:16}: {v}")

    print("\n  Mandatory improvements:")
    print(f"    expectancy improved : {comp['improved']['expectancy']}")
    print(f"    drawdown improved   : {comp['improved']['drawdown']}")
    print(f"    winrate improved    : {comp['improved']['winrate']}")


def main() -> None:
    log.info("EGX Radar Pro — rebuild edge")

    universe = SYMBOLS[:14]
    market_data = load_market_data(universe, bars=280)

    signal_preview(market_data, top_n=5)

    diag = diagnose_failure(market_data)
    _print_diagnosis(diag)

    comp = validate_old_vs_new(market_data)
    _print_comparison(comp)

    out = {
        "diagnosis": diag,
        "comparison": comp,
    }
    out_path = Path(__file__).parent / "egx_radar_pro_rebuild_results.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    log.info("Saved rebuild report: %s", out_path)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        log.error("VALIDATION FAILED: %s", exc)
        sys.exit(1)
