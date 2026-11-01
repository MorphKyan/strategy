# Platform Instructions

## Scope and Entrypoints

This directory owns the event-driven backtest, simulated portfolio, live-planning, and dashboard platform.

- Source: `src/platform_core/`
- Configs: `configs/`
- Tests: `tests/`
- Data and metadata: `data/`
- Raw artifacts: `results/`
- Reports: `reports/`

最终报告布局见根 `AGENTS.md` 的“产物目录”；实验和敏感性工具默认将自动摘要写入 `results/`。

Entrypoints resolve relative paths from `platform/`:

- Backtest: `.\env\Scripts\python.exe platform\scripts\run_platform_backtest.py --config configs\baseline_r1_domestic_rolling.yaml`
- Experiment: `.\env\Scripts\python.exe platform\scripts\run_platform_experiment.py --config configs\baseline_r1_domestic_rolling.yaml`
- Sensitivity: `.\env\Scripts\python.exe platform\scripts\run_sensitivity.py --config configs\baseline_r1_domestic_rolling.yaml`
- Data sync: `.\env\Scripts\python.exe platform\scripts\sync_platform_data.py --config configs\baseline_r1_domestic_rolling.yaml`
- All-market sync: `.\env\Scripts\python.exe platform\scripts\sync_all_market_data.py`
- Common range: `.\env\Scripts\python.exe platform\scripts\get_common_date_range.py --config platform\configs\baseline_r1_domestic_rolling.yaml`

Use `.\env\python.exe` instead when that is the project's actual Python layout. Do not reference missing configs.

## Implementation Rules

1. Strategy work must use `Strategy.generate_targets(context)`.
2. Strategy variants must be additive. Register a strategy in `BUILTIN_STRATEGIES` only when it is intended to be loaded by platform configs.
3. Remove failed or research-only strategy registrations and active candidate configs from the submitted diff; retain their final report and reproduction entrypoint. Clean regenerable research intermediates under the root artifact rules.
4. Preserve transaction costs, order handling, rejection handling, trade reporting, and the semantics of existing benchmarks unless the task explicitly changes them.
5. Avoid broad architecture rewrites during a strategy research task unless the user requests them.

## Config and Script Rules

- A reusable config under `configs/` must encode one strategy and one portfolio, use one `strategy` mapping, and contain no fixed `start_date` or `end_date`. Provide bounded windows at runtime.
- Keep temporary or generated research configs under `configs/generated/` or the owning research subsystem; do not overwrite baselines.
- Only reusable parameterized tools with a stable CLI belong under `scripts/`. Do not retain hardcoded config matrices, one-off report generators, or task-specific sweep scripts.
- 报告保留足以重建研究的脚本或配置，不要求两者都提供；运行时生成的配置和明细是临时产物，不注册为平台基线。

## Artifact Provenance

- Fixed configs are YAML files under `configs/`, excluding `configs/generated/`.
- Only a fixed config's full-common-history run may be written under `results/backtests/`. The window must cover the earliest through latest trading dates shared by all configured assets, and the latest date must pass the root freshness rule.
- Generated/non-fixed configs, bounded windows, experiments, training/final-test runs, and ad hoc setups belong under `results/temporary_backtests/`.
- Use `results/temporary_backtests/direct/` for temporary direct runs and `results/temporary_backtests/experiments/` for standardized experiments.
- Sensitivity artifacts and automated summaries stay under `results/sensitivity/`; include the final conclusion in the owning report under `reports/`.
- Streamlit loads only `results/backtests/` by default. It may include temporary backtests through one global option that defaults off, and must never load sensitivity artifacts.
- If provenance cannot prove both a fixed config and a full-common-history window, classify the result as temporary.

## Research Execution

Apply the root research mode:

- User-directed platform research: `default` + `stress`, plus two-calendar-month start-date sensitivity.
- Autonomous research: `default` + `stress` + `dynamic_participation` and the full `$run-autonomous-quant-research` protocol.

Identify the slippage scenario for every metric set. Compare annualized return, annualized volatility, Sharpe, max drawdown, turnover, trade count, order count, rejection count, pending-intent pressure, cash drag, and other task-relevant diagnostics.

Use `results/backtest_cache/` only when symbols, config hash or parameters, sample window, data snapshot, code version, and slippage scenario match. A data sync expires older entries unless they prove an equal or newer snapshot.
