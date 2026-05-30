# Experiment Report: risk_parity_ewma

## Goal
Run a standardized experiment for `risk_parity_ewma` and compare it against `risk_parity` when baseline metrics are available.

## Hypothesis
This run evaluates whether the candidate strategy improves risk-adjusted performance without an unreasonable turnover increase.

## Commands
- Candidate: `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\risk_parity.yaml --strategy risk_parity_ewma`
- Baseline: `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\risk_parity.yaml --strategy risk_parity`

## Candidate Metrics
- Total return: 64.02%
- Annualized return: 6.20%
- Annualized volatility: 3.50%
- Max drawdown: -3.80%
- Sharpe ratio: 1.7727
- Annualized turnover: 0.7159
- Trade count: 66
- Out-of-sample metrics available: False

## Baseline Comparison
- Sharpe delta: +0.0463
- Annualized return delta: +0.0015
- Annualized volatility delta: -0.0001
- Max drawdown delta: +0.0061
- Annualized turnover delta: +0.2410

## Recommendation
- Refine

## Notes
- Metrics are computed from generated CSV artifacts, not inferred from memory.
- Out-of-sample metrics are marked unavailable unless the repository explicitly generates them.
