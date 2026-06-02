# Quant Research Repo Rules

## Repository Layout

The repository has two separate systems:

- `research/`: original risk-parity research backtest system.
- `platform/`: daily event-driven retail backtest and simulated-portfolio platform.
- `etf_selection/`: standalone ETF sleeve screening and basket construction workflow.

Do not mix their source, configs, scripts, reports, or results. Shared workspace-level files are limited to root documentation, dependency files, `env/`, and archived `backup/` content.

## Research System Facts

- Baseline strategy: `research/src/strategies/risk_parity.py`
- Default risk-parity config: `research/configs/risk_parity.yaml`
- ETF universe for basket research: `research/configs/risk_parity_etf_universe.yaml`
- Main backtest entry: `.\env\python.exe research\main.py --config configs/risk_parity.yaml --strategy <name>`
- Standard experiment entry: `.\env\python.exe research\scripts\run_experiment.py --strategy <name> --config configs/risk_parity.yaml`
- Basket screening entry: `.\env\python.exe research\scripts\select_risk_parity_universe.py --write-configs`
- Raw backtest artifacts: `research/results/<strategy>/<timestamp>/`
- Standard experiment artifacts: `research/reports/experiments/<strategy>/<timestamp>/`
- Literature notes: `research/reports/literature/`
- Generated basket configs: `research/configs/generated/`
- Strategy modules are loaded dynamically from `research/src/strategies/<strategy>.py` and must expose `run_strategy(df, config)`.

Research entrypoints resolve relative paths from `research/`.

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

1. Never modify `research/src/strategies/risk_parity.py` unless the user explicitly asks to change the research baseline.
2. Create research strategy variants additively as new files under `research/src/strategies/`.
3. Keep research variants compatible with `research/main.py`: the module name must match `--strategy`, and it must return `(result_df, trades_df, metrics)`.
4. Platform strategy work must stay under `platform/` and use the platform `Strategy.generate_targets(context)` API.
5. Do not introduce deep learning, reinforcement learning, unrelated factor models, or broad architecture rewrites unless explicitly requested.
6. Do not run unrestricted parameter searches, silent optimizer sweeps, or broad benchmark changes.
7. Preserve transaction-cost handling and trade reporting. If backtest artifacts exist, report turnover and trade count.
8. Every research experiment must produce a markdown report under `research/reports/experiments/`.
9. Prefer low-complexity, literature-supported changes over speculative redesigns.
10. Keep the default ETF basket in `research/configs/risk_parity.yaml` as the fixed reference basket unless the user explicitly asks to replace it.
11. Do not overwrite generated historical results, reports, or configs unless the user explicitly asks.
12. 回测时如果发现数据与当前日期差距有一周以上请先获取数据再进行回测。

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

## ETF Basket Research Rules

- Basket selection is allowed only as an additive, reviewable research variant.
- Only use China-market ETFs defined in `research/configs/risk_parity_etf_universe.yaml` unless the user explicitly approves broader coverage.
- Prefer ETFs with longer adjusted local history and enough common overlap for backtests.
- Evaluate candidate baskets with risk-parity-aligned metrics:
  - cross-asset sleeve coverage
  - common history length
  - pairwise correlation
  - inverse-volatility concentration
- Prefer baskets with at least one equity ETF and one defensive sleeve such as government bonds or gold.
- Avoid redundant baskets that are only small substitutions of the same exposure.
- Write new basket configs under `research/configs/generated/` or another additive config path.
- Compare basket configs with:
  `.\env\python.exe research\scripts\run_experiment.py --strategy risk_parity --config <candidate-config> --baseline-config configs/risk_parity.yaml`

## Implementation Guidelines

- Read `README.md` plus the relevant subsystem README before making changes.
- All newly generated markdown reports and summaries must be written in Chinese. Keep code identifiers, file names, metric keys, and commands unchanged when clarity requires exact names.
- Reuse the current config schema unless a separate config is genuinely needed.
- Keep the research baseline config as the reference unless the experiment is explicitly a basket/config experiment.
- Use adjusted local ETF data as loaded by `research/src/data_handler.py`; do not silently change price adjustment or common-history handling.
- When using literature, save or cite notes under `research/reports/literature/` and do not claim literature support without sources.
- If out-of-sample metrics are unavailable in the repository, state that explicitly instead of inventing them.

## Validation Workflow For Research Experiments

Before claiming success:

1. Confirm the baseline entrypoint and candidate entrypoint.
2. Run the relevant command, usually:
   `.\env\python.exe research\scripts\run_experiment.py --strategy <name> --config configs/risk_parity.yaml`
3. Verify raw artifacts exist under `research/results/<strategy>/<timestamp>/`.
4. Verify standardized artifacts exist under `research/reports/experiments/<strategy>/<timestamp>/`.
5. Read generated metrics from `research/reports/experiments/<strategy>/<timestamp>/metrics.json`; do not infer them from memory.
6. Confirm the report includes hypothesis, files changed, exact command, metrics delta, turnover, trade count, and recommendation.

If the run fails, still report the exact command, the failure artifact path, and the likely next fix. Do not present a failed run as a completed experiment.

## Research Summary History

- 非基线研究价值成果汇总：[non_baseline_research_history_summary.md](file:///D:/strategy/platform/reports/non_baseline_research_history_summary.md)

