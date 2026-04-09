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
- If out-of-sample metrics are unavailable in the current repo, say so explicitly instead of inventing them.

## Suggested Daily Automation Prompt
Use the quant-research skill and subagents to run one disciplined research cycle for this repository.

Requirements:
- focus on risk-parity improvements only
- choose at most one low-complexity, literature-supported variant
- do not modify baseline
- implement the variant in a new file
- run the relevant backtest
- compare against baseline if metrics are available
- write a report under reports/experiments/
- if there is no high-confidence improvement to try, write a short no-change report instead
