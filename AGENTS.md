# Quant Research Repo Rules

## Objective
This repository is for controlled research on additive improvements around the current risk-parity baseline. Treat every change as a small, auditable experiment, not as an open-ended optimization exercise.

Codex should behave like a disciplined research engineer:
- inspect the existing workflow before changing code
- preserve the baseline unless explicitly asked otherwise
- make one clear hypothesis per experiment
- validate with repository commands and generated artifacts
- report negative or inconclusive results plainly

## Repo Facts
- Baseline strategy: `src/strategies/risk_parity.py`
- Default risk-parity config: `configs/risk_parity.yaml`
- ETF universe for basket research: `configs/risk_parity_etf_universe.yaml`
- Main backtest entry: `.\env\python.exe main.py --config configs/risk_parity.yaml --strategy <name>`
- Standard experiment entry: `.\env\python.exe scripts/run_experiment.py --strategy <name> --config configs/risk_parity.yaml`
- Basket screening entry: `.\env\python.exe scripts/select_risk_parity_universe.py --write-configs`
- Raw backtest artifacts: `results/<strategy>/<timestamp>/`
- Standard experiment artifacts: `reports/experiments/<strategy>/<timestamp>/`
- Literature notes: `reports/literature/`
- Generated basket configs: `configs/generated/`
- Strategy modules are loaded dynamically from `src/strategies/<strategy>.py` and must expose `run_strategy(df, config)`.

## Hard Rules
1. Never modify `src/strategies/risk_parity.py` unless the user explicitly asks to change the baseline.
2. Create strategy variants additively as new files under `src/strategies/`.
3. Keep variants compatible with `main.py`: the module name must match `--strategy`, and it must return `(result_df, trades_df, metrics)`.
4. Do not introduce deep learning, reinforcement learning, unrelated factor models, or broad architecture rewrites unless explicitly requested.
5. Do not run unrestricted parameter searches, silent optimizer sweeps, or broad benchmark changes.
6. Preserve transaction-cost handling and trade reporting. If backtest artifacts exist, report turnover and trade count.
7. Every experiment must produce a markdown report under `reports/experiments/`.
8. Prefer low-complexity, literature-supported changes over speculative redesigns.
9. Keep code changes small, reviewable, and limited to the requested research surface.
10. Keep the default ETF basket in `configs/risk_parity.yaml` as the fixed reference basket unless the user explicitly asks to replace it.
11. Do not overwrite generated historical results, reports, or configs unless the user explicitly asks.

## Preferred Experiment Scope
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
- Only use China-market ETFs defined in `configs/risk_parity_etf_universe.yaml` unless the user explicitly approves broader coverage.
- Prefer ETFs with longer adjusted local history and enough common overlap for backtests.
- Evaluate candidate baskets with risk-parity-aligned metrics:
  - cross-asset sleeve coverage
  - common history length
  - pairwise correlation
  - inverse-volatility concentration
- Prefer baskets with at least one equity ETF and one defensive sleeve such as government bonds or gold.
- Avoid redundant baskets that are only small substitutions of the same exposure.
- Write new basket configs under `configs/generated/` or another additive config path.
- Compare basket configs with:
  `.\env\python.exe scripts/run_experiment.py --strategy risk_parity --config <candidate-config> --baseline-config configs/risk_parity.yaml`

## Implementation Guidelines
- Read `README.md` and relevant source files before making research changes.
- Reuse the current config schema unless a separate config is genuinely needed.
- Keep the baseline config as the reference unless the experiment is explicitly a basket/config experiment.
- Use adjusted local ETF data as loaded by `src/data_handler.py`; do not silently change price adjustment or common-history handling.
- If online data fetching is required, prefer repository scripts and report that data was fetched.
- When using literature, save or cite notes under `reports/literature/` and do not claim literature support without sources.
- If out-of-sample metrics are unavailable in the repository, state that explicitly instead of inventing them.

## Variant Naming
Use descriptive strategy module names such as:
- `risk_parity_ewma`
- `risk_parity_vol_target`
- `risk_parity_shrinkage`
- `risk_parity_turnover_aware`

New configs should live under `configs/` or `configs/generated/` only when a separate config is actually needed.

## Validation Workflow
Before claiming success:
1. Confirm the baseline entrypoint and the candidate entrypoint.
2. Run the relevant command, usually:
   `.\env\python.exe scripts/run_experiment.py --strategy <name> --config configs/risk_parity.yaml`
3. Verify raw artifacts exist under `results/<strategy>/<timestamp>/`.
4. Verify standardized artifacts exist under `reports/experiments/<strategy>/<timestamp>/`.
5. Read generated metrics from `reports/experiments/<strategy>/<timestamp>/metrics.json`; do not infer them from memory.
6. Confirm the report includes hypothesis, files changed, exact command, metrics delta, turnover, trade count, and recommendation.

If the run fails, still report the exact command, the failure artifact path, and the likely next fix. Do not present a failed run as a completed experiment.

## Reporting Requirements
Every final experiment summary should include:
- hypothesis
- files changed
- exact command run
- raw result path
- standardized report path
- key metrics versus baseline when available
- turnover and trade count
- whether out-of-sample metrics are available
- accept, reject, or refine recommendation

For non-experiment documentation or maintenance tasks, keep the response focused on what changed and how it was checked.

## Recurring Research Prompt
For scheduled or repeated research cycles, use this task shape:

Run one disciplined risk-parity research cycle for this repository. Focus only on low-complexity, literature-supported improvements. Choose at most one variant unless explicitly asked for more. Basket screening is allowed when justified by risk-parity criteria, but generated configs must stay additive. Do not modify the baseline strategy. Implement the variant in a new file, run the relevant backtest, compare against baseline when metrics are available, and write the report under `reports/experiments/`. If there is no high-confidence improvement to try, write a short no-change report instead of forcing a change.
