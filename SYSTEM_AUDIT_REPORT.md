# EGX Radar Full System Audit Report

Date: 2026-03-25
Reviewer mode: Quant + Trading + Software Architecture

## 1) System Overview
EGX Radar is a multi-layer discretionary/systematic hybrid for EGX equities:
- Core scanner and ranking in egx_radar/core
- Backtest simulation in egx_radar/backtest
- Outcomes logging in egx_radar/outcomes
- Platform/API/WebSocket in egx_radar/dashboard
- Database persistence in egx_radar/database
- AI/News/Alpha context layers in egx_radar/ai

Current practical behavior:
- Price action and SmartRank are primary.
- AI/news/alpha are additive context layers and can be toggled.
- Main historical simulation path runs through run_backtest() in egx_radar/backtest/engine.py.

## 2) Architecture Evaluation
Strengths:
- Modular separation between scanner, backtest, risk guards, and platform.
- Core signal path remains mostly deterministic and testable.
- Distinct files for data quality, momentum, and portfolio constraints.

Weaknesses:
- Legacy scripts and verification utilities are not fully synchronized with current core signatures.
- Some integration pieces are implemented but consistency relies on conventions and helper scripts.
- Multiple tactical layers (AI/news/alpha) can create validation complexity if not constrained by strict gates.

## 3) Code Quality Review
Strengths:
- Clear decomposition and typed return signatures in many modules.
- Good use of helper functions and isolated domain files.

Issues found:
- Hardcoded numeric constants in trade math where config constants are safer.
- Runtime utility scripts can drift out-of-date when core API contracts evolve.
- Several safety checks for non-finite numeric inputs were missing in backtest path.

## 4) Trading Strategy Evaluation
Professional view:
- Entry framework is viable for continuation and accumulation behavior.
- Position sizing model is coherent but sensitive to invalid numeric fields in pending trades.
- Partial-profit logic was stable conceptually but had duplicated magic-number usage.

Bias/edge view:
- Signal quality depends heavily on guard integrity and realistic execution assumptions.
- Alpha early-entry overlays can produce edge only under strict gating and low turnover.

## 5) Risk Management Review
Strengths:
- Explicit stop, target, and max hold mechanics.
- Sector and open-trade caps exist.

Critical risk controls improved during this pass:
- Added runtime clamps to account and risk getters.
- Added NaN/non-finite hardening in trade open sizing path.
- Replaced hardcoded partial fractions with config constant for consistency.

## 6) Backtesting Integrity Check
What is good:
- Walk-forward style loop without direct look-ahead reads in core path.
- Costs and slippage modeled.

Observed integrity risks and fixes:
- Utility script mismatch with run_backtest return shape caused false failures.
  - Fixed in _run_single_bt.py to support 3 or 4 tuple outputs.
- Non-finite values in pending trade fields could crash simulation.
  - Fixed with finite checks and sanitized defaults in _build_open_trade().

## 7) AI & Probability Evaluation
- Probability engine is integrated as secondary confidence layer.
- It remains bounded and does not replace SmartRank.
- Validation scenario confirms non-degradation after hardening changes.

## 8) News & Alpha Evaluation
- News sentiment and alpha modules are now modular and optional.
- Alpha is constrained by strict filter rules and risk scaling.
- Validation comparison currently passes approval gates in the existing harness:
  - Expectancy improves
  - Drawdown acceptable
  - No overtrading
  - Early trades show edge

## 9) Identified Problems (Detailed)
High:
1. Backtest stability risk from non-finite pending fields in sizing path.
2. Operational drift risk from script/core signature mismatch.

Medium:
3. Hardcoded partial-exit fraction duplicated in multiple modules.
4. Runtime parameter accessors lacked robust range clamps.

Low:
5. Entry-point path mutation in package __main__ was unnecessary and fragile.

## 10) Fixes Applied (With Reasoning)
1. settings.py
- Added PARTIAL_EXIT_FRACTION config.
- Added validation clamps:
  - get_account_size(): fallback if non-finite or too small.
  - get_risk_per_trade(): clamp to sane range.
Reason: eliminate invalid runtime risk inputs and centralize partial logic.

2. backtest/engine.py
- Hardened _build_open_trade() against NaN/non-finite account, entry, risk_pct, target_pct, risk_amount, and risk_per_share.
- Replaced hardcoded 0.5 partial math with K.PARTIAL_EXIT_FRACTION.
Reason: prevent crashes and ensure consistent risk accounting.

3. outcomes/engine.py
- Replaced hardcoded 0.5 partial math with K.PARTIAL_EXIT_FRACTION.
Reason: parity with backtest and centralized configuration.

4. _run_single_bt.py
- Updated unpacking logic to handle current run_backtest() 4-value return.
Reason: restore operational compatibility for verification runs.

5. egx_radar/__main__.py
- Removed redundant sys.path mutation.
Reason: safer packaging/runtime behavior.

## Rebuild Deliverable
A complete standalone production-style engine has been created:
- egx_radar_pro_system.py
It includes:
- Configuration and EGX universe
- Snapshot and Trade data classes
- Indicators and SmartRank
- Regime and sector analysis
- AI probability and learning
- News sentiment and strength
- Alpha score/filter/execution
- Risk-managed signal generation
- Backtest simulation
- Baseline vs AI vs Alpha validation
- Main execution with result export

## Auditor Conclusion
The system is structurally strong but was vulnerable to numerical robustness and operational drift issues that can invalidate confidence in results. Those high-impact reliability issues were fixed. The alpha/news layers now remain optional, constrained, and validated against explicit approval gates. The rebuilt one-file engine demonstrates an end-to-end production blueprint that is executable and risk-aware.
