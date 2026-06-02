# Expanded China ETF Basket Top 3 Comparison

## Scope
Compare the top 3 ETF baskets from the latest China ETF basket screening against the fixed default basket in `configs/risk_parity.yaml`.

## Important Note
This round was run after fixing the shared-history alignment logic in `src/data_handler.py`, so all candidate baskets and the baseline now use the same common end date instead of forward-filling stale prices.

## Source Screen
- Basket screen: `reports/literature/20260409_172804_china_etf_basket_screen.md`

## Baseline
- Basket: `510300 + 511260 + 518880`
- Common window: `2017-08-24` to `2026-03-16`
- 年化收益率： `6.05%`
- 年化波动率： `3.51%`
- 最大回撤： `-4.41%`
- Sharpe: `1.7257`
- 年化换手： `0.4771`

## Top 3 Results
| Basket | Screen Score | Annualized Return | Annualized Vol | Max Drawdown | Sharpe | Annualized Turnover | Read |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `510880 + 511260 + 518880` | `0.8404` | `5.74%` | `3.34%` | `-4.13%` | `1.7199` | `0.4272` | Lower return and Sharpe than baseline, but lower turnover and slightly better drawdown |
| `510050 + 511260 + 518880` | `0.8326` | `5.90%` | `3.48%` | `-4.09%` | `1.6955` | `0.4770` | Better drawdown, but weaker Sharpe and slightly weaker return |
| `510180 + 511260 + 518880` | `0.8301` | `5.91%` | `3.44%` | `-4.58%` | `1.7199` | `0.4339` | Best Sharpe among the top 3 baskets, but still slightly below baseline and with worse drawdown |

## 底层报告
- `reports/experiments/risk_parity/20260409_172812/report.md`
- `reports/experiments/risk_parity/20260409_172825/report.md`
- `reports/experiments/risk_parity/20260409_172840/report.md`

## 建议
Refine, not accept.

The expanded universe gave us more credible equity sleeve choices, but none of the top 3 baskets beat the current baseline on risk-adjusted return. The strongest practical alternatives are:

1. `510880 + 511260 + 518880` if the goal is lower turnover and slightly shallower drawdown.
2. `510180 + 511260 + 518880` if the goal is to stay close to the baseline Sharpe while modestly reducing turnover.

For the next round, the most promising path is not a pure basket swap. A better test would be to combine the strongest accepted strategy variant, `risk_parity_ewma_semiannual`, with the best one or two candidate baskets from this report.
