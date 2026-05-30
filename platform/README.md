# Retail Backtest Platform

This directory contains the newer daily event-driven platform runtime. It is separate from the original risk-parity research system under `research/`.

## Directory Map

- `scripts/run_platform_backtest.py`: platform backtest entrypoint.
- `scripts/run_platform_experiment.py`: standardized experiment runner with candidate/baseline comparison.
- `scripts/run_sim_portfolio.py`: create or advance a simulated portfolio from a checkpoint.
- `scripts/sync_platform_data.py`: sync platform market and fundamental data.
- `scripts/run_sensitivity.py`: start-date sensitivity analysis.
- `scripts/validate_hfq_data.py`: compare platform adjusted close against the research HFQ chain.
- `src/platform_core/`: platform engine package.
  - `models.py`: assets, bars, positions, orders, trades, portfolio state.
  - `engine.py`: daily event-driven backtest engine.
  - `execution.py`: target-weight execution, fees, lot sizing, suspension and price-limit checks.
  - `strategy.py`: platform strategy API and built-in strategies.
  - `data.py`, `data_store.py`, `data_sources.py`: local CSV data, normalization, and Finshare integration.
  - `metrics.py`: research-grade metrics computed from platform artifacts.
  - `visualization.py`: low-coupling chart rendering from persisted CSV artifacts.
  - `experiment.py`: experiment orchestration and report/archive writing.
  - `data_validation.py`: HFQ data-chain comparison helpers.
  - `sim.py`: simulated portfolio continuation from checkpoints.
  - `storage.py`: SQLite metadata store.
- `configs/`: platform YAML configs.
- `data/`: platform-owned market data and SQLite metadata.
- `docs/`: platform planning and architecture decisions.
- `reports/`: platform reports.
- `results/`: platform raw run artifacts.
- `tests/`: platform unit and integration tests.

## Commands

Run from the repository root:

```powershell
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\platform_mvp.yaml
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\platform_risk_parity.yaml
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\platform_risk_parity.yaml
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\platform_risk_parity.yaml
.\env\python.exe platform\scripts\validate_hfq_data.py --codes 510300 518880 511260
.\env\python.exe platform\scripts\sync_platform_data.py --config configs\platform_m3m4.yaml
.\env\python.exe platform\scripts\run_sim_portfolio.py --config configs\platform_m3m4.yaml --checkpoint <checkpoint.json> --asof-date 2026-05-30
```

The platform scripts change their working directory to `platform/`, so relative paths such as `configs/platform_mvp.yaml`, `data/`, and `results/platform/` are platform-local.

## Implemented Capabilities

- Daily event loop with per-day checkpoints.
- Target-weight strategies and multi-segment date scheduling.
- Cash, position, cost-basis, pending-intent, and cooldown state.
- Fee, lot-size, suspension, limit-up, and limit-down execution checks.
- Retry, cancel, or mark-failed handling for unfilled intents.
- Built-in equal-weight, fundamental-filtered equal-weight, and risk-parity strategies.
- Point-in-time fundamental filtering where local fundamental data exists.
- SQLite metadata for strategy versions, backtests, checkpoints, simulated portfolios, and references.
- Standardized experiment reports with optional baseline comparison under `reports/experiments/`.
- Research-grade metrics: annualized return, volatility, max drawdown, Sharpe, turnover, trade/order counts, rejection counts, pending-intent pressure, and cash drag.
- CSV-only visualization module for NAV/drawdown, position weights, cash/pending-intent effects, and rejected-order reasons.
- Start-date sensitivity analysis with default 3-trading-day step and no sample cap.
- HFQ validation against the old research data chain.

## Archive Structure

- Raw direct backtests: `results/backtests/<run_id>/`
- Raw standardized experiments: `results/backtests/<experiment>/<timestamp>/<strategy>/<run_id>/`
- Standardized experiment reports: `reports/experiments/<experiment>/<timestamp>/`
- Sensitivity raw runs: `results/sensitivity_raw/<strategy>/<timestamp>/`
- Sensitivity reports: `reports/sensitivity/<strategy>/<timestamp>/`
- Data validation reports: `reports/data_validation/<timestamp>/`

Raw run directories contain execution-level artifacts. Report directories contain decision-level summaries, metrics, config copies, and pointers back to raw paths.

## Research Parity Notes

See `docs/research_feature_parity.md` for which research-system features are already represented in the platform and which need additional implementation.

## TODO

### ETF Basket Screening

Build a platform-native basket screening workflow instead of reusing the research script directly.

What to build:
- Add `configs/platform_etf_universe.yaml` using the platform asset schema: `asset_id`, `code`, `name`, `asset_type`, `exchange`, `currency`, `lot_size`, and `price_limit_pct`.
- Add `scripts/select_platform_universe.py`.
- Read platform-local data through `MarketDataStore` or `LocalCsvBarData`; do not depend on `research/src/data_handler.py`.
- Score candidate baskets with risk-parity-aligned criteria: sleeve coverage, common history length, average absolute correlation, inverse-volatility concentration, and defensive sleeve inclusion.
- Write generated configs to `configs/generated/platform_basket_*.yaml`.
- Write reports to `reports/literature/etf_screening/<timestamp>/`.
- Add a follow-up command that can immediately run `scripts/run_platform_experiment.py` on each generated candidate against `configs/platform_risk_parity.yaml`.

How to do it:
- Start by porting the scoring math from `research/scripts/select_risk_parity_universe.py`.
- Replace research config writing with platform config writing.
- Keep the default platform risk-parity config unchanged.
- Add tests using a temporary three-ETF data directory with known correlations and history overlap.

### Literature And Research Notes

Create a platform research-note flow for strategy and execution-model decisions.

What to build:
- Add `reports/literature/` as the platform location for research notes.
- Add a small helper or template under `docs/templates/experiment_note.md`.
- Require notes to record: hypothesis, source or rationale, expected execution-model impact, platform files touched, exact command, metrics delta, execution rejection summary, and recommendation.
- Link standardized experiment reports back to any related literature note.

How to do it:
- Keep notes plain Markdown so they remain reviewable.
- For execution-model changes, prefer ADRs under `docs/adr/`.
- For strategy ideas, use `reports/literature/<date>_<topic>.md`.
- Do not claim literature support without a source or a clearly marked internal rationale.

### Not Planned

- The old research strategy plugin interface `run_strategy(df, config)` will not be migrated. Platform strategies should use `Strategy.generate_targets(context)`.
