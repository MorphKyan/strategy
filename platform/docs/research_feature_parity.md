# Research System Feature Parity

This note compares the original `research/` risk-parity workflow with the newer `platform/` runtime.

## Already Implemented In Platform

- A platform-native risk-parity strategy exists as `RiskParityStrategy` in `platform/src/platform_core/strategy.py`.
- Platform configs can express the same default ETF basket used by the research baseline.
- The platform can calculate inverse-volatility weights from rolling close history.
- The platform supports quarterly-style rebalances and threshold checks.
- Transaction costs, trade records, and turnover-style aggregate metrics are generated.
- Raw artifacts are written under `platform/results/`.
- Checkpoints are written for every processed trading day.
- Standardized experiment reports are available through `platform/scripts/run_platform_experiment.py`, including optional baseline comparison and `metrics.json`.
- Research-grade metrics are computed by `platform/src/platform_core/metrics.py`.
- Low-coupling chart rendering is available through `platform/src/platform_core/visualization.py`.
- Start-date sensitivity analysis is available through `platform/scripts/run_sensitivity.py` with default step `3` and no sample cap.
- HFQ chain validation is available through `platform/scripts/validate_hfq_data.py`.

## Not Yet Equivalent

- ETF basket screening remains research-only. The platform can run a selected basket, but it does not yet select baskets from `risk_parity_etf_universe.yaml`.
- Research strategy modules expose `run_strategy(df, config)`. Platform strategies use `Strategy.generate_targets(context)`, so research variants cannot run unchanged on platform. This interface migration is intentionally not planned.
- Existing research reports and historical metrics contain paths and schemas from the old system; they are preserved under `research/reports/` and are not automatically converted.

## Remaining Work

- Port ETF basket screening to write platform configs under `platform/configs/generated/`.
- Add platform literature/research-note templates and links from experiment reports.
- Build a strategy-level validation report that compares research `risk_parity` and platform `risk_parity` on the same basket and dates.

The main caveat is exact result identity. Because the platform models orders, lot size, pending fills, price limits, suspensions, and checkpointed state more explicitly, a platform run may intentionally differ from the older vector-style research backtest even when the strategy idea is the same.
