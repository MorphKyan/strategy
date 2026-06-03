# Quant Research Repo Rules

## Repository Layout

The repository has two separate systems:

- `platform/`: daily event-driven retail backtest and simulated-portfolio platform.
- `etf_selection/`: standalone ETF sleeve screening and basket construction workflow.

Do not mix their source, configs, scripts, reports, or results. Shared workspace-level files are limited to root documentation, dependency files, and `env/`.

## Platform System Facts

- Platform source: `platform/src/platform_core/`
- Platform configs: `platform/configs/`
- Platform docs: `platform/docs/`
- Platform tests: `platform/tests/`
- Platform backtest entry: `.\env\python.exe platform\scripts\run_platform_backtest.py --config configs/platform_mvp.yaml`
- Platform risk-parity config: `platform/configs/platform_risk_parity.yaml`
- Platform data sync entry: `.\env\python.exe platform\scripts\sync_platform_data.py --config configs/platform_m3m4.yaml`
- Platform simulated portfolio entry: `.\env\python.exe platform\scripts\run_sim_portfolio.py --config configs/platform_m3m4.yaml --checkpoint <checkpoint.json> --asof-date <YYYY-MM-DD>`
- Platform raw artifacts: `platform/results/`
- Platform reports: `platform/reports/`
- Platform metadata/data: `platform/data/`

Platform entrypoints resolve relative paths from `platform/`.

## ETF Selection Facts

- ETF selection source: `etf_selection/src/`
- ETF selection config: `etf_selection/config/etf_universe.yaml`
- ETF selection entry: `.\env\python.exe etf_selection\scripts\screen_etf_sleeves.py --config etf_selection\config\etf_universe.yaml`
- ETF selection agent rules: `etf_selection/AGENTS.md`
- Generated platform configs: `etf_selection/generated_configs/<timestamp>/`
- ETF selection reports: `etf_selection/reports/<timestamp>/`

ETF selection is independent from `platform/`; it may generate platform configs and call platform CLI commands, but platform internals should not depend on ETF selection.

## Hard Rules

1. Platform strategy work must stay under `platform/` and use the platform `Strategy.generate_targets(context)` API.
2. Create strategy variants additively under `platform/src/platform_core/strategy.py` or modify the configuration parameter options to fit.
3. Keep strategy variants registered in `BUILTIN_STRATEGIES` so they can be loaded by the platform engine.
4. Do not introduce deep learning, reinforcement learning, unrelated factor models, or broad architecture rewrites unless explicitly requested.
5. Do not run unrestricted parameter searches, silent optimizer sweeps, or broad benchmark changes.
6. Preserve transaction-cost handling and trade reporting. If backtest artifacts exist, report turnover and trade count.
7. Do not overwrite generated historical results, reports, or configs unless the user explicitly asks.
8. 回测时如果发现数据与当前日期差距有一周以上请先获取数据再进行回测。

## Preferred Research Scope

Prefer research ideas adjacent to risk parity:

- volatility estimation changes, such as EWMA or robust rolling volatility
- covariance shrinkage or robust covariance
- volatility targeting overlays
- rebalance frequency or threshold changes
- turnover-aware constraints
- ETF basket selection within the configured China ETF universe

Avoid:

- unrelated alpha or factor models
- benchmark or asset-universe changes hidden inside a strategy variant
- large refactors during a research task
- post-hoc parameter tuning after seeing backtest results

## Implementation Guidelines

- Read `README.md` plus the relevant subsystem README before making changes.
- All newly generated markdown reports and summaries must be written in Chinese. Keep code identifiers, file names, metric keys, and commands unchanged when clarity requires exact names.
- Reuse the current config schema unless a separate config is genuinely needed.
- If out-of-sample metrics are unavailable in the repository, state that explicitly instead of inventing them.

## Validation Workflow For Platform Experiments

Before claiming success:

1. Confirm the baseline configurations and candidate configurations.
2. Run the platform experiment:
   - **For strategy updates**: Run backtests using the new strategy for **all platform configurations** in `platform/configs/` and compare all results.
   - **For ETF sleeve expansion**: Run backtests for the expanded portfolio using **multiple strategy algorithms** (e.g., `risk_parity`, `risk_parity_ewma`, `risk_parity_ewma_dd_recovery`) and compare all results.
3. Manage and utilize the shared backtest cache:
   - Save backtest results in the shared directory `platform/results/backtest_cache/` in JSON format with a `timestamp`.
   - Before running a backtest, check if a valid cache exists.
   - If a data sync (`sync_platform_data.py`) was triggered due to outdated data during the task, mark all existing cache entries generated before the sync timestamp as expired, and rebuild/update them.
4. Verify raw artifacts exist under `platform/results/`.
5. Verify standardized artifacts exist under `platform/reports/`.
6. Read generated metrics from `platform/reports/experiments/<strategy>/<timestamp>/metrics.json`; do not infer them from memory.
7. Confirm the report includes hypothesis, files changed, exact commands, metrics delta for all configurations/algorithms, turnover, trade count, and recommendation.

## Research Summary History

- 非基线研究价值成果汇总：[non_baseline_research_history_summary.md](file:///D:/strategy/platform/reports/non_baseline_research_history_summary.md)
