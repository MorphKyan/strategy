# EWMA Volatility Note

## Idea
Use exponentially weighted moving volatility in the risk-parity allocator instead of a simple rolling standard deviation.

## Why This Is Reasonable
- It is a standard low-complexity extension of inverse-volatility sizing.
- It reacts faster to recent risk regime shifts than a flat rolling window.
- It keeps the strategy interpretable and compatible with the current backtest interface.

## Expected Benefit
- More responsive risk estimates during volatility transitions.
- Potentially smoother drawdown control if recent turbulence matters more than stale history.

## Implementation Mapping
- Add a new strategy module under `src/strategies/`.
- Reuse the existing quarterly rebalance and transaction cost logic.
- Only replace the volatility estimator used to derive target weights.
