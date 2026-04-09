# Quant Research Repo Rules

## Objective
This repository is used for controlled research on additive strategy improvements around the current risk-parity baseline.
Codex should behave like a disciplined research engineer, not an unconstrained optimizer.

## Repo Facts
- Baseline strategy file: `src/strategies/risk_parity.py`
- Default risk-parity config: `configs/risk_parity.yaml`
- Main backtest entry: `.\env\python.exe main.py --config configs/risk_parity.yaml --strategy <name>`
- Standardized experiment entry: `.\env\python.exe scripts/run_experiment.py --strategy <name> --config configs/risk_parity.yaml`
- Raw backtest artifacts: `results/<strategy>/<timestamp>/`
- Standardized experiment reports: `reports/experiments/<strategy>/<timestamp>/`
- Literature notes: `reports/literature/`

## Hard Rules
1. Never modify the baseline strategy implementation unless the user explicitly asks for it.
2. Always create additive variants in new files under `src/strategies/`.
3. Do not introduce deep learning, RL, or unrelated factor models unless explicitly requested.
4. Do not perform unrestricted parameter search or silent optimizer sweeps.
5. Always preserve transaction cost handling and report turnover if backtest artifacts exist.
6. Every experiment must produce a markdown summary under `reports/experiments/`.
7. Prefer low-complexity, literature-supported changes over speculative redesigns.
8. Keep code changes small, auditable, and compatible with the current `main.py` workflow.
9. Keep the default ETF basket in `configs/risk_parity.yaml` as the fixed reference basket unless the user explicitly asks to replace it.

## ETF Basket Research Rules
- ETF basket selection is allowed for research variants, but it must be additive and reviewable.
- Only use China-market ETFs defined in `configs/risk_parity_etf_universe.yaml` unless the user explicitly approves broader coverage.
- Prefer ETFs with longer adjusted local history and enough common overlap for backtests.
- Evaluate candidate baskets using metrics aligned with risk parity:
  - cross-asset sleeve coverage
  - common history length
  - pairwise correlation
  - inverse-vol concentration
- Prefer baskets with at least one equity ETF and one defensive sleeve such as government bond or gold.
- Avoid redundant baskets that are only small code-level substitutions of the same exposure.
- New basket configs should go under `configs/generated/` or another additive config path.

## Variant Naming
- Use names like:
  - `risk_parity_ewma`
  - `risk_parity_vol_target`
  - `risk_parity_shrinkage`
- New configs should live under `configs/` only when a separate config is actually needed.

## Validation Workflow
Before claiming success:
1. Confirm the intended baseline and variant entrypoints.
2. Run the relevant backtest command.
3. Verify raw artifacts exist in `results/`.
4. Write a standardized report in `reports/experiments/`.
5. Summarize:
   - hypothesis
   - files changed
   - exact command run
   - key metrics delta
   - accept/reject/refine recommendation

## Preferred Experiment Scope
Prefer:
- volatility estimation changes
- covariance shrinkage or robust covariance
- volatility targeting overlays
- rebalance frequency adjustment
- turnover-aware constraints
- ETF basket selection within the China ETF universe when justified by risk-parity criteria

Avoid:
- broad architecture rewrites
- silent benchmark changes
- unrelated refactors during research tasks
