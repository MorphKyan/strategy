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
- Platform backtest entry: `.\env\python.exe platform\scripts\run_platform_backtest.py --config configs/baseline_mvp_equal_weight.yaml`
- Platform risk-parity config: `platform/configs/baseline_r1_domestic_rolling.yaml`
- Platform data sync entry: `.\env\python.exe platform\scripts\sync_platform_data.py --config configs/baseline_m3m4_fundamental.yaml`
- Platform simulated portfolio entry: `.\env\python.exe platform\scripts\run_sim_portfolio.py --config configs/baseline_m3m4_fundamental.yaml --checkpoint <checkpoint.json> --asof-date <YYYY-MM-DD>`
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
8. 回测时如果发现数据与当前日期差距有一周以上请先获取数据再进行回测（同步数据时需使用与该课题/选定 ETF 组合匹配的配置文件，不一定是固定的 `baseline_m3m4_fundamental.yaml`）。
9. QuantResearcher 认领课题时，应按照看板中的顺序由上至下依次认领第一个处于 Todo 状态的课题，不需自行挑选。
10. 研究阶段必须固定样本切分：`2025-07-01`（含）之后的数据为最终测试样本；策略构思、ETF 选择、参数选择、阈值设定、候选筛选、缓存复用和报告中的研究结论不得使用测试样本信息。
11. 所有平台研究在提交前必须执行起点敏感性测试：在不触碰最终测试样本的前提下，从该配置/组合的最早可用交易日开始，到训练样本末日（最晚 `2025-06-30`）为止，每隔 2 个月生成一个 `start_date`，逐一起跑回测并报告核心指标是否稳定。
12. 只有在训练样本内研究通过、起点敏感性测试稳定，并且固定后的策略/组合在 `2025-07-01`（含）之后最终测试样本中仍表现良好时，QuantResearcher 才允许提交成果；否则必须标记为“Failed”或“仅研究观察”，不得合入或注册为可投策略。

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
2. Enforce the fixed sample split:
   - Training/research sample: data up to `2025-06-30`.
   - Final test sample: data from `2025-07-01` onward.
   - Do not inspect, tune, rank, select, or reject candidates using the final test sample before the research candidate is frozen.
3. Run the platform experiment:
   - **For strategy updates**: Run backtests using the new strategy for **all platform configurations** in `platform/configs/` and compare all results.
   - **For ETF sleeve expansion**: Run backtests for the expanded portfolio using **multiple strategy algorithms** (e.g., `risk_parity`, `risk_parity_ewma`, `risk_parity_ewma_dd_recovery`) and compare all results.
4. Run start-date sensitivity:
   - For each candidate/baseline configuration or algorithm, generate start dates from the earliest available common date to the training-sample end date, stepping by 2 calendar months.
   - Run or reuse valid cached backtests for each start date, keeping the end date capped at `2025-06-30`.
   - Report whether ranking, Sharpe, max drawdown, turnover, trade count, and rejection count materially change across start dates.
5. Run the final test stage only after the candidate is frozen:
   - Use `2025-07-01` and later data only in this stage.
   - Do not change strategy code, parameters, ETF basket membership, rebalance rules, or acceptance thresholds after seeing test results.
   - A candidate may be submitted only if the final test sample remains acceptable versus its baseline and does not introduce worse execution risk.
6. Manage and utilize the shared backtest cache:
   - Save backtest results in the shared directory `platform/results/backtest_cache/` in JSON format with a `timestamp`.
   - Before running a backtest, check if a valid cache exists.
   - If a data sync (`sync_platform_data.py`) was triggered due to outdated data during the task, mark all existing cache entries generated before the sync timestamp as expired, and rebuild/update them.
7. Verify raw artifacts exist under `platform/results/`.
8. Verify standardized artifacts exist under `platform/reports/`.
9. Read generated metrics from `platform/reports/experiments/<strategy>/<timestamp>/metrics.json`; do not infer them from memory.
10. Confirm the report includes hypothesis, files changed, exact commands, metrics delta for all configurations/algorithms, start-date sensitivity results, final test-sample metrics, turnover, trade count, and recommendation.

## Research Summary History

- 非基线研究价值成果汇总：[non_baseline_research_history_summary.md](file:///D:/strategy/platform/reports/non_baseline_research_history_summary.md)

## 研究辅助工具 (Research Utility Tools)

为了在研究和回测中提高配置生成的便利性与稳定性，我们在 `platform/scripts/` 下提供了一系列工具：

1. **无配置依赖数据同步工具 (Sync All Market Data)**:
   - **执行命令**: `.\env\python.exe platform/scripts/sync_all_market_data.py`
   - **说明**: 自动从 Finshare 获取并同步组合内全部 12 个 ETF 标的的最新的市场日线数据和基本面指标数据，直到当前日期。此脚本独立运行，不依赖于任何配置文件。
   - **参数**:
     - `--start-date <YYYY-MM-DD>` (默认值: `2010-01-01`): 从指定日期开始同步。
     - `--no-fundamentals`: 跳过基本面财务指标数据的同步。
     - `--data-dir <path>` (默认值: `data`): 指定保存市场数据的本地目录。
     - `--fundamentals-dir <path>` (默认值: `data/platform_fundamentals`): 指定保存基本面财务指标数据的本地目录。

2. **最长公共历史时段计算工具 (Get Common Date Range)**:
   - **执行命令**: `.\env\python.exe platform/scripts/get_common_date_range.py --config platform/configs/baseline_r3_global_nasdaq_all_weather_ewma.yaml`
   - **说明**: 计算指定配置或标的列表在本地数据中的最长公共历史交易时段（历史数据的交集）。这有助于在回测时动态对齐并稳定 `start_date` 和 `end_date`。
   - **参数**:
     - `--config <path1> <path2> ...`: 从一个或多个平台配置文件中加载标的列表。
     - `--codes <code1> <code2> ...`: 直接指定一个或多个标的代码。
     - `--data-dir <path>` (默认值: `data`): 本地市场数据存储目录。
     - 例如: `.\env\python.exe platform/scripts/get_common_date_range.py --codes 510300 518880 511260`
