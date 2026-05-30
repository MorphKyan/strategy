# Experiment Report: risk_parity

## Goal
Run a standardized experiment for `risk_parity` and compare it against `risk_parity` when baseline metrics are available.

## Hypothesis
This run evaluates whether the candidate strategy improves risk-adjusted performance without an unreasonable turnover increase.

## Commands
- Candidate: `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\risk_parity.yaml --strategy risk_parity`

## Candidate Metrics
- Total return: 62.12%
- Annualized return: 6.05%
- Annualized volatility: 3.50%
- Max drawdown: -4.41%
- Sharpe ratio: 1.7264
- Annualized turnover: 0.4749
- Trade count: 48
- Out-of-sample metrics available: False

## Baseline Comparison
- No baseline comparison was written because baseline metrics were not available.

## Recommendation
- Review

## Notes
- Metrics are computed from generated CSV artifacts, not inferred from memory.
- Out-of-sample metrics are marked unavailable unless the repository explicitly generates them.
