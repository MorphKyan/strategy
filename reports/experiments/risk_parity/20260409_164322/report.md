# Experiment Report: risk_parity

## Goal
Run a standardized experiment for `risk_parity` and compare it against `risk_parity` when baseline metrics are available.

## Hypothesis
This run evaluates whether the candidate strategy improves risk-adjusted performance without an unreasonable turnover increase.

## Commands
- Candidate: `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_3_510300_510880_511260_518880.yaml --strategy risk_parity`
- Baseline: `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\risk_parity.yaml --strategy risk_parity`

## Candidate Basket
- `510300` 沪深300ETF
- `510880` 红利ETF
- `511260` 十年国债ETF
- `518880` 黄金ETF

## Baseline Basket
- `510300` 沪深300ETF
- `518880` 黄金ETF
- `511260` 十年国债ETF

## Candidate Metrics
- Total return: 59.68%
- Annualized return: 5.81%
- Annualized volatility: 3.91%
- Max drawdown: -6.79%
- Sharpe ratio: 1.4861
- Annualized turnover: 0.4442
- Trade count: 56
- Out-of-sample metrics available: False

## Baseline Comparison
- Sharpe delta: -0.2402
- Annualized return delta: -0.0024
- Annualized volatility delta: +0.0041
- Max drawdown delta: -0.0239
- Annualized turnover delta: -0.0307

## Recommendation
- Refine

## Notes
- Metrics are computed from generated CSV artifacts, not inferred from memory.
- Out-of-sample metrics are marked unavailable unless the repository explicitly generates them.
