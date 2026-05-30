# EWMA Semiannual Summary

## Hypothesis
Combine EWMA volatility estimation with a semiannual rebalance calendar to keep the responsiveness benefit of EWMA while reducing unnecessary trading.

## Files Changed
- `src/strategies/risk_parity_ewma_semiannual.py`
- `reports/literature/20260409_semiannual-rebalance-note.md`

## Command Run
- `.\env\python.exe scripts\run_experiment.py --strategy risk_parity_ewma_semiannual --config configs\risk_parity.yaml --baseline-strategy risk_parity`

## Key Metric Delta vs Baseline
- Annualized return: `+0.52%`
- Annualized volatility: `+0.09%`
- Max drawdown: improved by about `1.01%`
- Sharpe ratio: `+0.1033`
- Annualized turnover: `+0.0586`
- Trade count: `42` vs `48`

## Relative Read vs Prior EWMA Variant
- Better annualized return than `risk_parity_ewma`
- Better Sharpe than `risk_parity_ewma`
- Better max drawdown than `risk_parity_ewma`
- Much lower annualized turnover than `risk_parity_ewma` (`0.5335` vs `0.7159`)

## Recommendation
Accept as the strongest candidate so far in this repo.

It improves return, Sharpe, and drawdown versus the baseline while keeping turnover only modestly above the original strategy and materially below the first EWMA variant.
