"""
utils/helpers.py — EGX Radar Pro
===================================
Pure utility functions with no internal project dependencies.
Safe to import from any module.
"""

from __future__ import annotations


def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp a float value to the closed interval [lo, hi]."""
    return max(lo, min(hi, x))


def pct_change(new_val: float, old_val: float) -> float:
    """Percentage change from old_val to new_val, avoiding division by zero."""
    return (new_val - old_val) / max(abs(old_val), 1e-9) * 100.0


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Division that returns default when denominator is near zero."""
    return numerator / denominator if abs(denominator) > 1e-9 else default
