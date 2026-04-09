# Repo-Specific Codex Notes

## Quick Facts
- Baseline strategy: `src/strategies/risk_parity.py`
- Alternative existing strategy: `src/strategies/balanced.py`
- Main backtest entry: `.\env\python.exe main.py --config configs/risk_parity.yaml --strategy <name>`
- Recommended research entry: `.\env\python.exe scripts/run_experiment.py --strategy <name> --config configs/risk_parity.yaml`
- Raw result root: `results/<strategy>/<timestamp>/`
- Standardized report root: `reports/experiments/<strategy>/<timestamp>/`
- Literature notes root: `reports/literature/`

## Expectations
- Do not edit `src/strategies/risk_parity.py` for routine research cycles.
- Implement variants as additive files under `src/strategies/`.
- Use `scripts/run_experiment.py` when a stable report artifact is needed.
- Use `scripts/select_risk_parity_universe.py` when research should screen ETF baskets instead of assuming the user-provided basket.
- If out-of-sample metrics are unavailable in the current repo, say so explicitly instead of inventing them.

## ETF Basket Screening
- China ETF candidate pool: `configs/risk_parity_etf_universe.yaml`
- Basket screening entry: `.\env\python.exe scripts/select_risk_parity_universe.py --write-configs`
- Fetch missing local ETF data before screening when needed:
  - `.\env\python.exe scripts/select_risk_parity_universe.py --fetch-missing --write-configs`
- Generated basket configs: `configs/generated/`
- Basket comparison can be done with:
  - `.\env\python.exe scripts/run_experiment.py --strategy risk_parity --config <candidate-config> --baseline-config configs/risk_parity.yaml`

## Suggested Daily Automation Prompt
Use the quant-research skill and subagents to run one disciplined research cycle for this repository.

Requirements:
- focus on risk-parity improvements only
- choose at most one low-complexity, literature-supported variant
- allow screening alternative China ETF baskets when justified by risk-parity criteria
- do not modify baseline
- implement the variant in a new file
- run the relevant backtest
- compare against baseline if metrics are available
- write a report under reports/experiments/
- if there is no high-confidence improvement to try, write a short no-change report instead
