# EWMA Variant Summary

## 假设
Replacing simple rolling volatility with EWMA volatility may improve risk-adjusted performance by reacting faster to recent regime changes while preserving the existing risk-parity structure.

## Files Changed
- `src/strategies/risk_parity_ewma.py`
- `reports/literature/20260409_ewma-risk-note.md`

## Command Run
- `.\env\python.exe scripts\run_experiment.py --strategy risk_parity_ewma --config configs\risk_parity.yaml --baseline-strategy risk_parity`

## Key Metric Delta vs Baseline
- 年化收益率： `+0.15%`
- 年化波动率： `-0.01%`
- 最大回撤： improved by about `0.61%`
- 夏普比率： `+0.0463`
- 年化换手： `+0.2410`
- 成交笔数： `66` vs `48`

## 建议
Refine, not accept yet.

The EWMA variant improved return, drawdown, and Sharpe slightly, but it paid for that with a material turnover increase. A reasonable next step would be to keep the EWMA estimator and test a stricter rebalance gate or a turnover-aware overlay before promoting it.
