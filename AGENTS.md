# Quant Research Repo Rules

## Repository Layout

This workspace contains two independent systems:

- `platform/`: daily event-driven retail backtest and simulated-portfolio platform.
- `etf_selection/`: standalone ETF sleeve screening and basket construction workflow.

Do not mix their source, configs, scripts, reports, or results. Shared workspace-level files are limited to root documentation, dependency files, agent configuration, and `env/`.

## Canonical Rule Sources

- This file is the canonical workspace rule file.
- `etf_selection/AGENTS.md` may add ETF-selection-specific rules, but must not weaken this file.
- `.agents/agents/*/agent.json` are harness prompts. They must summarize or reference these rules instead of introducing conflicting gates.
- Deprecated or duplicate instruction files should be deleted instead of kept as separate rule sources.

When documents conflict, apply this priority order: user instruction for the current task, this file, subsystem `AGENTS.md`, harness prompts, README files.

## Platform System Facts

- Platform source: `platform/src/platform_core/`
- Platform configs: `platform/configs/`
- Platform docs: `platform/docs/`
- Platform tests: `platform/tests/`
- Platform raw artifacts: `platform/results/`
- Platform reports: `platform/reports/`
- Platform metadata/data: `platform/data/`
- Platform backtest entry: `.\env\Scripts\python.exe platform\scripts\run_platform_backtest.py --config configs\baseline_r1_domestic_rolling.yaml` (or `.\env\python.exe` when the local env uses that layout)
- Platform experiment entry: `.\env\Scripts\python.exe platform\scripts\run_platform_experiment.py --config configs\baseline_r1_domestic_rolling.yaml` (or `.\env\python.exe` when the local env uses that layout)
- Platform sensitivity entry: `.\env\Scripts\python.exe platform\scripts\run_sensitivity.py --config configs\baseline_r1_domestic_rolling.yaml` (or `.\env\python.exe` when the local env uses that layout)
- Platform data sync entry: `.\env\Scripts\python.exe platform\scripts\sync_platform_data.py --config configs\baseline_r1_domestic_rolling.yaml` (or `.\env\python.exe` when the local env uses that layout)
- Platform all-market data sync entry: `.\env\Scripts\python.exe platform\scripts\sync_all_market_data.py` (or `.\env\python.exe` when the local env uses that layout)
- Platform common date range entry: `.\env\Scripts\python.exe platform\scripts\get_common_date_range.py --config platform\configs\baseline_r1_domestic_rolling.yaml` (or `.\env\python.exe` when the local env uses that layout)

Platform entrypoints resolve relative paths from `platform/`. Do not use commands that reference missing configs.

## ETF Selection Facts

- ETF selection source: `etf_selection/src/`
- ETF selection config: `etf_selection/config/etf_universe.yaml`
- ETF selection entry: `.\env\Scripts\python.exe etf_selection\scripts\screen_etf_sleeves.py --config etf_selection\config\etf_universe.yaml` (or `.\env\python.exe` when the local env uses that layout)
- ETF selection agent rules: `etf_selection/AGENTS.md`
- Generated platform configs: `etf_selection/generated_configs/<timestamp>/`
- ETF selection reports: `etf_selection/reports/<timestamp>/`

ETF selection is independent from `platform/`; it may generate platform configs and call platform CLI commands, but platform internals must not depend on ETF selection.

## Hard Rules

1. Use the project Python on Windows: prefer `.\env\Scripts\python.exe` for venv/uv layouts; use `.\env\python.exe` when the local environment is laid out that way.
2. Platform strategy work must stay under `platform/` and use the platform `Strategy.generate_targets(context)` API.
3. Strategy variants must be additive. Register a strategy in `BUILTIN_STRATEGIES` only when it is intended to be loadable by platform configs. Failed or research-only variants must not remain registered in the submitted diff.
4. Do not introduce deep learning, reinforcement learning, unrelated factor models, broad architecture rewrites, hidden benchmark changes, or unrestricted parameter searches unless explicitly requested.
5. Preserve transaction-cost handling and trade reporting. If backtest artifacts exist, report turnover, trade count, order count, and rejection count.
6. Do not overwrite generated historical results, reports, configs, checkpoints, or raw execution artifacts unless the user explicitly asks.
7. Agent-created temporary scripts used for backtests, analysis, or one-off reporting must be deleted before task completion.
8. Reusable platform configs under `platform/configs/`, including retained generated configs, may be kept when they encode one strategy and one portfolio useful for baseline/candidate comparison. These configs must not include fixed backtest `start_date` or `end_date`; runtime commands must provide sample windows when a bounded sample is required. Platform configs must use a single `strategy` mapping and must not use multi-segment strategy schedules.
9. Only reusable, parameterized tools may be added under `platform/scripts/`. Do not add task-specific backtest scripts, hardcoded config matrices, hardcoded strategy sweeps, or one-off report generators there. A retained script must have a stable CLI, avoid hardcoded research config lists, document its usage, and have a clear maintenance owner.
10. All newly generated markdown reports and summaries must be written in Chinese. Keep code identifiers, file names, metric keys, and commands unchanged when exactness matters.

## Data Freshness And Sample Isolation

1. Before using market data for screening, research, backtests, or generated configs, verify that every required symbol is aligned and that the latest local date is no more than 7 calendar days before the current date.
2. If data are stale, sync all required symbols and re-check alignment before continuing. If sync or alignment fails, stop the task and report the failure; do not backtest, screen, or output configs.
3. Fixed sample split:
   - Training/research sample: data up to `2025-06-30`.
   - Final test sample: data from `2025-07-01` onward.
4. Research ideas, ETF selection, parameter choices, thresholds, candidate filtering, cache reuse decisions, and research conclusions must not use final test-sample information.
5. A platform config or ETF basket may be output or submitted only when the common available history from the earliest shared trading date through `2025-06-30` is longer than 3 years.
6. Final test results may be run only after the candidate strategy, parameters, ETF basket, rebalance rules, and acceptance thresholds are frozen. Do not modify the candidate after seeing final test results.

## Platform Research Validation

Before claiming a platform research result is successful:

1. Confirm the baseline and candidate configs or algorithms.
2. Run training-sample comparisons with runtime backtest end date capped at `2025-06-30`.
3. Every platform backtest, experiment, sensitivity run, and final test validation must include all three required slippage scenarios: `default`, `stress`, and `dynamic_participation`. The `default` scenario uses ordinary fixed bps slippage, `stress` uses widened fixed bps slippage, and `dynamic_participation` adds trade-value-versus-daily-amount impact on top of ordinary slippage. Reports must identify the slippage scenario for every metric set and must not claim a candidate is successful unless execution risk is acceptable under all three scenarios.
4. Scope the comparison set explicitly:
   - Strategy API or engine changes: active non-generated baseline configs under `platform/configs/`.
   - Strategy-variant research: the baseline configs relevant to the claimed asset universe, plus any config where the variant is intended to be used.
   - ETF sleeve expansion: multiple built-in strategy algorithms, for example `risk_parity`, `risk_parity_ewma`, and `risk_parity_ewma_dd_recovery`.
   - Generated, demo, or archived configs are included only when the claim depends on them or the user asks.
5. Run start-date sensitivity without touching the final test sample. Generate one runtime `start_date` every 2 calendar months from the earliest common available trading date through `2025-06-30`, and cap every run at `2025-06-30`.
6. Report whether ranking, Sharpe, annualized return, max drawdown, turnover, trade count, order count, and rejection count materially change across start dates and across the three slippage scenarios.
7. Use `platform/results/backtest_cache/` only for cache entries whose symbols, config hash or parameter set, sample window, data freshness timestamp, code version, and slippage scenario match the requested run. Cache entries using `2025-07-01` or later data must not be reused for research decisions.
8. If a data sync occurred, treat older cache entries as expired unless they can prove they were generated from the same or newer data snapshot.
9. Run final test-sample validation only after the candidate is frozen.
10. Verify raw artifacts exist under `platform/results/` and standardized artifacts exist under `platform/reports/`.
11. Read generated metrics from actual artifacts, preferably `metrics.json`; do not infer metrics from memory.
12. Reports must include hypothesis, files changed, exact commands, baseline/candidate metrics, start-date sensitivity, final test-sample metrics if run, turnover, trade count, rejection count, slippage-scenario metrics, and recommendation.

## Acceptance Guidance

- A candidate may be submitted only if training-sample comparisons pass, start-date sensitivity is stable, final test-sample performance remains acceptable versus baseline, and execution risk does not worsen materially.
- If a candidate only has local advantage, is unstable, overfits, increases annualized two-sided turnover by more than 30% without clear compensating benefit, or fails final testing, mark it as `Failed` or `research-only`.
- Research-only findings may be summarized in `platform/reports/non_baseline_research_history_summary.md` and `research-dashboard/research_history_summary.md`, but should not leave registered strategy code or new platform baseline configs behind.

## Research Orientation

For platform strategy implementation tasks, prefer ideas adjacent to risk parity:

- volatility estimation changes, such as EWMA or robust rolling volatility
- covariance shrinkage or robust covariance
- volatility targeting overlays
- rebalance frequency or threshold changes
- turnover-aware constraints
- ETF basket selection within the configured ETF universe

Topic exploration may be broader when the idea can be validated in this repository and the report clearly states the expected validation path, risk, and cost. Avoid hidden benchmark changes, large refactors during a research task, and post-hoc tuning after seeing backtest results. Deep learning, reinforcement learning, broad factor models, and large parameter searches are allowed only when explicitly requested or clearly marked as exploratory rather than default implementation work.
