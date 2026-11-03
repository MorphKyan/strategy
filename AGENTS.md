# Strategy Workspace Instructions

## Project Positioning

This repository is a quantitative strategy development and simulation workspace. It supports:

- platform engineering and maintenance;
- user-directed research and historical scenario analysis;
- an explicitly invoked autonomous research pipeline.

Do not treat every backtest as autonomous candidate discovery. Follow the user's stated research direction, instruments, window, and intended strength of conclusion. The autonomous protocol applies only when the user asks agents to select or claim research directions themselves, or explicitly invokes `$run-autonomous-quant-research` / `$orchestrate-quant-research`.

## Repository Layout

- `platform/`: daily event-driven retail backtest and simulated-portfolio platform.
- `etf_selection/`: standalone ETF sleeve screening and basket construction workflow.
- `research-dashboard/`: autonomous-research backlog, notes, review handoffs, and history.
- `.agents/`: repository agents and task-specific skills.
- `env/`: shared project Python environment.

Keep `platform/` and `etf_selection/` source, configs, scripts, reports, and results independent. ETF selection may generate platform configs and call platform CLI commands, but platform internals must not depend on ETF selection.

Read the closest subsystem `AGENTS.md` before working below that directory. User instructions for the current task take priority; an agent harness or skill may add stricter rules for its own workflow but must not silently broaden its scope.

## Workspace Rules

1. On Windows, use the project Python: prefer `.\env\Scripts\python.exe`; use `.\env\python.exe` when that is the environment's actual layout.
2. Protect final reports, source market data, live/sim portfolio state, and recovery checkpoints. Regenerable research intermediates are temporary: clean them after report completion and reproduction verification, rather than archiving them.
3. Delete agent-created temporary scripts before completion. Retained tools must be parameterized; a report's reproduction script is a permanent deliverable.
4. Write newly generated Markdown reports, research notes, dashboards, and summaries in Chinese. Preserve exact commands, paths, identifiers, and metric keys where needed.
5. Read metrics from actual artifacts, preferably `metrics.json`; do not reconstruct results from memory.

## 产物目录

- 各子系统的 `reports/` 只放研究，课题直接使用 `reports/<课题键>/<YYYYMMDD>/report.md`，不再分 `research`、`engineering`、`live` 或 `screening` 层。课题键使用研究 ID 加主题，无 ID 时直接用主题；同日正式修订加 `_02`。
- 每次发布保留 `report.md` 和一个可执行的复现入口：脚本或配置即可，不强制同时提供脚本、配置目录和 manifest。必要配图与附录可随报告保留；试跑不创建报告版本。
- 执行入口应一次生成报告所需的运行配置、中间数据、图表和汇总，覆盖候选、对照及正式验证情景，不依赖上次保留的中间结果。报告写明执行命令、代码与依赖版本、基础数据来源及版本。
- 两个子系统统一使用 `configs/` 保存正式可复用配置，运行时生成的配置只写入各自的 `results/configs/<课题键>/<运行ID>/`，不进入 Git，不在正式配置目录下另设 generated 层。
- 中间配置、CSV、日志、缓存和试跑结果仅在 `results/` 临时产生，完成报告并确认能重新生成后清理，不长期存档。历史报告缺少生成入口时，允许将必要的原始 YAML 随同报告放入 `reports/<课题键>/<版本>/configs/`，明确标注“完整复现尚未验证”；不能据此宣称可复现或自动升级为正式配置。基础行情、账户状态与恢复检查点按原有职责保存，不作为研究中间文件清理。
- `reports/README.md` 是研究报告索引；看板链接同一份报告。实盘展示输出放 `results/live_reports/`，不进入研究报告目录或 Git。
- 整理时直接更新引用，不保留旧路径副本或转发文件。复现必须实际运行核验；历史脚本或输入缺失时明确标注，不能只凭文件齐全宣称可复现。

## Market Data Preconditions

Before market-data screening, research, backtests, or config generation:

1. Verify every required symbol is aligned and its latest local date is no more than 7 calendar days before the current date.
2. If data are stale, sync all required symbols and re-check freshness and alignment.
3. If sync or alignment fails, stop the affected research or backtest and report the failure. Do not continue with stale or misaligned data, including for bounded historical analysis.

## Research Standards

These standards apply to both user-directed and autonomous research:

- State the hypothesis or question, instruments, `asset_type`, sample window, price/NAV convention, benchmark, transaction-cost assumptions, and intended conclusion.
- Prevent look-ahead. Data used at a decision point must have been available at that point; respect publication and reporting lags.
- Preserve transaction-cost handling and trade reporting. When artifacts exist, report annualized return, annualized volatility, Sharpe, max drawdown, turnover, trade count, order count, and rejection count, plus other metrics material to the question.
- For platform strategy or portfolio research, run start-date sensitivity using one runtime start date every calendar month across the applicable research window. Report material changes in ranking and core metrics.
- Distinguish exploratory evidence from an executable recommendation. Clearly disclose limitations caused by short history, selected windows, proxy assets, missing liquidity, or non-tradable instruments.

### User-directed research

When the user defines the direction, instruments, or historical window:

- Use the requested window; the repository's autonomous training/final-test split does not apply unless the user opts into it.
- Run the `default` and `stress` slippage scenarios for platform backtests, experiments, and sensitivity analysis. In this repository, `stress` is the fixed-bps pressure scenario.
- Run `dynamic_participation` only when the user requests it, when participation/liquidity impact is central to the question, or when the conclusion is being promoted to autonomous-style candidate acceptance.
- Do not add autonomous topic-selection preferences or acceptance thresholds that the user did not request.

### Autonomous research

When agents choose or claim research directions themselves, read and follow `.agents/skills/run-autonomous-quant-research/SKILL.md`. That skill owns the fixed sample split, candidate freeze, three-scenario execution validation, minimum-history gate, acceptance rules, and independent review workflow. Do not copy those values back into this file.

## Instrument Semantics

### Published indices

Published financial indices (`asset_type: index`, for example `000300`, `000015`, and `CBA21801`) may be used in virtual buy/sell simulations, historical scenario analysis, and algorithm evaluation. They are non-tradable benchmarks:

- label index results as research simulations;
- do not use index liquidity or simulated fills as evidence of executable capacity;
- do not replace a live executable portfolio with an index.

Any executable live recommendation must map to real tradable ETF or futures instruments with actual market volume and liquidity.

### QDII ETFs

For conclusions that depend on a QDII ETF (`513*`, `159920`, `159941`, and equivalents):

- report market-price and NAV-caliber annualized return and endpoint premium levels for each sample window;
- state the premium at the intended entry point for live recommendations;
- obtain decision inputs through `platform/src/platform_core/etf_premium.py` and its publication-lag guard, never a raw same-day price/NAV ratio.

NAV data are written by `platform/scripts/fetch_etf_nav.py` under `platform/data/etf_nav/`. See `platform/reports/R056-A_qdii_premium_feasibility/20261101/report.md` for the rationale and measured contamination example.
