# EWMA Variant Summary

## Hypothesis
Replacing simple rolling volatility with EWMA volatility may improve risk-adjusted performance by reacting faster to recent regime changes while preserving the existing risk-parity structure.

## Files Changed
- `src/strategies/risk_parity_ewma.py`
- `reports/literature/20260409_ewma-risk-note.md`

## Command Run
- `.\env\python.exe scripts\run_experiment.py --strategy risk_parity_ewma --config configs\risk_parity.yaml --baseline-strategy risk_parity`

## Key Metric Delta vs Baseline
- Annualized return: `+0.15%`
- Annualized volatility: `-0.01%`
- Max drawdown: improved by about `0.61%`
- Sharpe ratio: `+0.0463`
- Annualized turnover: `+0.2410`
- Trade count: `66` vs `48`

## Recommendation
Refine, not accept yet.

The EWMA variant improved return, drawdown, and Sharpe slightly, but it paid for that with a material turnover increase. A reasonable next step would be to keep the EWMA estimator and test a stricter rebalance gate or a turnover-aware overlay before promoting it.
