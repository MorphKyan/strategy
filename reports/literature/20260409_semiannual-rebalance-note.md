# Semiannual Rebalance Note

## Idea
Reduce rebalance frequency from quarterly to semiannual while keeping the EWMA volatility estimator.

## Why This Is Reasonable
- Rebalance frequency is a standard, low-complexity control knob in allocation strategies.
- Lower rebalance frequency often reduces turnover and trading frictions.
- The change remains transparent and easy to audit in the current codebase.

## Expected Benefit
- Lower realized turnover than the quarterly EWMA variant.
- A chance to keep most of the drawdown and Sharpe improvement if the signal is not overly short-lived.

## Implementation Mapping
- Add a new strategy module under `src/strategies/`.
- Reuse the existing target-weight logic and transaction cost accounting.
- Only change the rebalance calendar from quarterly to semiannual.
