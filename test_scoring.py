"""Quick validation of adaptive source scoring."""
import pandas as pd
import numpy as np
from egx_radar.data.source_scoring import (
    score_source, rank_sources, cache_best_source,
    get_cache_snapshot, QUALITY_THRESHOLD, FALLBACK_THRESHOLD,
)

dates = pd.date_range("2025-01-01", periods=120, freq="B")

# Yahoo: full data, good quality
df_yahoo = pd.DataFrame({
    "Open": np.random.uniform(10, 20, 120),
    "High": np.random.uniform(15, 25, 120),
    "Low": np.random.uniform(5, 15, 120),
    "Close": np.random.uniform(10, 20, 120),
    "Volume": np.random.randint(1000, 100000, 120),
}, index=dates)

# Stooq: shorter data, zero volume
df_stooq = pd.DataFrame({
    "Open": np.random.uniform(10, 20, 60),
    "High": np.random.uniform(15, 25, 60),
    "Low": np.random.uniform(5, 15, 60),
    "Close": np.random.uniform(10, 20, 60),
    "Volume": [0] * 60,
}, index=dates[:60])

# TD: short, some NaN Close
close_td = [np.nan] * 5 + list(np.random.uniform(10, 20, 35))
df_td = pd.DataFrame({
    "Open": np.random.uniform(10, 20, 40),
    "High": np.random.uniform(15, 25, 40),
    "Low": np.random.uniform(5, 15, 40),
    "Close": close_td,
    "Volume": np.random.randint(500, 50000, 40),
}, index=dates[:40])

# Score individual sources
s1 = score_source(df_yahoo, "Yahoo", "TEST")
s2 = score_source(df_stooq, "Stooq", "TEST")
s3 = score_source(df_td, "TD", "TEST")

print("=== Individual Scores ===")
for name, sc in [("Yahoo", s1), ("Stooq", s2), ("TD", s3)]:
    print(f"  {name:6s}: total={sc['total']:.2f}  miss={sc['missing_pct']:.2f}  "
          f"vol={sc['volume_score']:.2f}  len={sc['length_score']:.2f}  "
          f"rec={sc['recency_score']:.2f}")

# Verify Yahoo > Stooq > TD in ranking
assert s1["total"] > s2["total"], "Yahoo should score higher than Stooq"
assert s1["total"] > s3["total"], "Yahoo should score higher than TD"

# Rank them
candidates = [(df_yahoo, "Yahoo"), (df_stooq, "Stooq"), (df_td, "TD")]
ranked = rank_sources(candidates, "TEST")
print("\n=== Adaptive Ranking ===")
for i, (_, lbl, sc) in enumerate(ranked):
    print(f"  #{i+1}: {lbl} score={sc['total']:.2f}")
assert ranked[0][1] == "Yahoo", "Yahoo should be ranked #1"

# Test fallback: when Yahoo is bad, other sources win
df_bad_yahoo = pd.DataFrame({
    "Open": [np.nan] * 40,
    "High": [np.nan] * 40,
    "Low": [np.nan] * 40,
    "Close": [np.nan] * 30 + list(np.random.uniform(10, 20, 10)),
    "Volume": [0] * 40,
}, index=dates[:40])

ranked2 = rank_sources(
    [(df_bad_yahoo, "Yahoo"), (df_stooq, "Stooq"), (df_td, "TD")], "TEST2"
)
print("\n=== Fallback Test (bad Yahoo) ===")
for i, (_, lbl, sc) in enumerate(ranked2):
    print(f"  #{i+1}: {lbl} score={sc['total']:.2f}")
assert ranked2[0][1] != "Yahoo", "Bad Yahoo should NOT be ranked #1"

# Test None source
s_none = score_source(None, "Empty", "TEST")
assert s_none["total"] == 0.0, "None source should score 0"

# Test cache
cache_best_source("TEST", "Yahoo")
snap = get_cache_snapshot()
assert snap["TEST"] == "Yahoo", "Cache should store best source"

# Thresholds
assert 0 < QUALITY_THRESHOLD < FALLBACK_THRESHOLD < 1.0, "Thresholds should be ordered"

print("\n=== ALL TESTS PASSED ===")
