# Experiment Report: risk_parity

## Goal
Run a standardized experiment for `risk_parity` and compare it against `risk_parity` when baseline metrics are available.

## Hypothesis
This run evaluates whether the candidate strategy improves risk-adjusted performance without an unreasonable turnover increase.

## Commands
- Candidate: `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_510180_511260_518880.yaml --strategy risk_parity`
- Baseline: `C:\Users\MorphKyan\tm-strategy\env\python.exe main.py --config C:\Users\MorphKyan\tm-strategy\configs\risk_parity.yaml --strategy risk_parity`

## Candidate Basket
- `510180` 上证180ETF
- `511260` 十年国债ETF
- `518880` 黄金ETF

## Baseline Basket
- `510300` 沪深300ETF
- `518880` 黄金ETF
- `511260` 十年国债ETF

## Candidate Metrics
- Total return: 60.33%
- Annualized return: 5.91%
- Annualized volatility: 3.44%
- Max drawdown: -4.58%
- Sharpe ratio: 1.7199
- Annualized turnover: 0.4339
- Trade count: 42
- Out-of-sample metrics available: False

## Baseline Comparison
- Sharpe delta: -0.0058
- Annualized return delta: -0.0014
- Annualized volatility delta: -0.0007
- Max drawdown delta: -0.0017
- Annualized turnover delta: -0.0433

## Recommendation
- Refine

## Notes
- Metrics are computed from generated CSV artifacts, not inferred from memory.
- Out-of-sample metrics are marked unavailable unless the repository explicitly generates them.
