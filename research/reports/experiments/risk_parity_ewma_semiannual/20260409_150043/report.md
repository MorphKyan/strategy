# Experiment Report: risk_parity_ewma_semiannual

## Goal
Run a standardized experiment for `risk_parity_ewma_semiannual` and compare it against `risk_parity` when baseline metrics are available.

## Hypothesis
This run evaluates whether the candidate strategy improves risk-adjusted performance without an unreasonable turnover increase.

## Commands
- Candidate: `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\risk_parity.yaml --strategy risk_parity_ewma_semiannual`
- Baseline: `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\risk_parity.yaml --strategy risk_parity`

## Candidate Metrics
- Total return: 68.76%
- Annualized return: 6.57%
- Annualized volatility: 3.59%
- Max drawdown: -3.39%
- Sharpe ratio: 1.8297
- Annualized turnover: 0.5335
- Trade count: 42
- Out-of-sample metrics available: False

## Baseline Comparison
- Sharpe delta: +0.1033
- Annualized return delta: +0.0052
- Annualized volatility delta: +0.0009
- Max drawdown delta: +0.0101
- Annualized turnover delta: +0.0586

## Recommendation
- Accept

## Notes
- Metrics are computed from generated CSV artifacts, not inferred from memory.
- Out-of-sample metrics are marked unavailable unless the repository explicitly generates them.
