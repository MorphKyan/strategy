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
2. Do not overwrite historical results, reports, generated configs, checkpoints, or raw execution artifacts unless the user explicitly requests it.
3. Delete agent-created temporary scripts before completion. Retained scripts must be reusable and parameterized rather than task-specific.
4. Write newly generated Markdown reports, research notes, dashboards, and summaries in Chinese. Preserve exact commands, paths, identifiers, and metric keys where needed.
5. Read metrics from actual artifacts, preferably `metrics.json`; do not reconstruct results from memory.

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
- For platform strategy or portfolio research, run start-date sensitivity using one runtime start date every 2 calendar months across the applicable research window. Report material changes in ranking and core metrics.
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

NAV data are written by `platform/scripts/fetch_etf_nav.py` under `platform/data/etf_nav/`. See `platform/reports/r056_qdii_premium_feasibility_audit.md` for the rationale and measured contamination example.
