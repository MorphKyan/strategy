# 红利袖子替换样本外稳定性分析

## 目标

本次分析覆盖 `platform/configs/*.yaml` 中非 `generated` 且包含 `512890` 红利低波ETF的 17 个配置。对每个配置保持策略算法、参数、交易成本、调仓规则、非红利资产不变，只把 `512890` 红利袖子替换为三种方案：

- `single_515080`：仅使用 `515080` 中证红利ETF。
- `single_563020`：仅使用 `563020` 红利低波ETF易方达。
- `split_515080_563020`：同时使用 `515080` 和 `563020`。

因为 `563020` 的本地历史从 `2023-12-14` 才开始，本次把每个配置的开始日期统一调整为 `max(原配置 start_date, 2023-12-14)`，结束日期保持原配置不变。这个共同历史窗口不再用于选参或训练，全部作为样本外稳定性观察区间。

## 产物

- 结构化指标：`platform/reports/experiments/dividend_sleeve_oos_matrix/20260624_213021/metrics.json`
- 逐次回测表：`platform/reports/experiments/dividend_sleeve_oos_matrix/20260624_213021/runs.csv`
- 原始回测产物：`platform/results/backtests/dividend_sleeve_oos_matrix/20260624_213021`
- 完成回测：51/51，失败：0。

## 数据与命令

- 数据最新日期：所有本次用到的本地行情均到 `2026-06-24`。
- 回测命令：在 `D:\strategy` 下通过 `.\env\python.exe -` 执行内存生成配置的批量回测脚本，调用 `PlatformBacktestEngine` 和 `build_platform_metrics`；未新增平台源码或临时脚本文件。
- 覆盖配置：17 个非 generated、含 `512890` 的配置，包括 `baseline_r1_*`、`baseline_r2_*`、`baseline_r3_*`、`baseline_us_blend_ewma`、对应 `risk_parity_cvar_dynamic_budget` 配置，以及 `demo_r1_domestic_ewma_cov`。

## 跨配置均值

| 替换方案 | 年化收益均值 | 年化波动均值 | 最大回撤均值 | Sharpe 均值 | 年化换手均值 | 成交均值 | 订单均值 | 拒单均值 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `single_515080` | 18.83% | 7.37% | -4.77% | 2.573 | 73.38% | 79.2 | 191.4 | 112.1 |
| `single_563020` | 18.60% | 7.24% | -4.69% | 2.584 | 69.73% | 75.7 | 197.7 | 122.0 |
| `split_515080_563020` | 17.08% | 7.39% | -4.83% | 2.335 | 69.35% | 86.2 | 242.6 | 156.4 |

## 稳定性计数

- 年化收益最高：`single_515080` 赢 13/17，`single_563020` 赢 4/17，`split_515080_563020` 赢 0/17。
- Sharpe 最高：`single_563020` 赢 10/17，`single_515080` 赢 7/17，`split_515080_563020` 赢 0/17。
- 最大回撤最浅：`split_515080_563020` 赢 10/17，`single_563020` 赢 5/17，`single_515080` 赢 2/17。
- 年化波动最低：`single_563020` 赢 11/17，`single_515080` 赢 4/17，`split_515080_563020` 赢 2/17。
- 年化换手最低：`split_515080_563020` 赢 8/17，`single_563020` 赢 6/17，`single_515080` 赢 3/17。
- 拒单最少：`single_515080` 赢 9/17，`single_563020` 赢 6/17，`split_515080_563020` 赢 2/17。

## 每配置综合最佳

综合评分使用 `Sharpe + 2 * max_drawdown`，偏向风险调整收益并惩罚回撤。17 个配置中，`single_563020` 为综合最佳 9 次，`single_515080` 为综合最佳 8 次，`split_515080_563020` 为 0 次。

| 配置 | 综合最佳 | 年化收益 | 最大回撤 | Sharpe |
|---|---|---:|---:|---:|
| `baseline_r1_domestic_ewma` | `single_563020` | 20.35% | -4.01% | 2.657 |
| `baseline_r1_domestic_low_vol_ewma` | `single_515080` | 18.97% | -3.92% | 2.635 |
| `baseline_r1_domestic_rolling` | `single_515080` | 18.51% | -5.21% | 2.652 |
| `baseline_r2_global_dividend_ewma` | `single_563020` | 17.65% | -4.67% | 2.522 |
| `baseline_r2_global_ewma` | `single_563020` | 18.75% | -5.01% | 2.627 |
| `baseline_r3_global_nasdaq_all_weather_ewma` | `single_563020` | 17.47% | -5.49% | 2.466 |
| `baseline_us_blend_ewma` | `single_563020` | 20.92% | -5.53% | 2.723 |
| `demo_r1_domestic_ewma_cov` | `single_563020` | 9.61% | -3.09% | 2.511 |
| `r1_domestic_ewma_10y_bond_3x_vol` | `single_563020` | 21.93% | -7.05% | 2.172 |
| `r1_domestic_ewma_30y_bond_futures` | `single_563020` | 20.35% | -4.01% | 2.657 |
| `r1_domestic_ewma_risk_parity_cvar_dynamic_budget` | `single_515080` | 20.74% | -3.08% | 2.907 |
| `r1_domestic_rolling_10y_bond_3x_vol` | `single_515080` | 22.44% | -5.92% | 2.241 |
| `r1_domestic_rolling_30y_bond_futures` | `single_515080` | 18.51% | -5.21% | 2.652 |
| `r2_global_dividend_ewma_risk_parity_cvar_dynamic_budget` | `single_515080` | 17.57% | -4.19% | 2.702 |
| `r2_global_ewma_risk_parity_cvar_dynamic_budget` | `single_563020` | 20.37% | -3.83% | 2.893 |
| `r3_global_nasdaq_all_weather_ewma_risk_parity_cvar_dynamic_budget` | `single_515080` | 17.31% | -4.66% | 2.517 |
| `us_blend_ewma_risk_parity_cvar_dynamic_budget` | `single_515080` | 18.55% | -4.53% | 2.751 |

## 解读

`single_515080` 的优势在收益和执行层面更清楚。它在 13/17 个配置里给出最高年化收益，拒单最少的次数也是最多的；缺点是平均波动和平均换手略高于 `single_563020`。

`single_563020` 的优势在风险调整收益和稳定性。它的均值 Sharpe 略高于 `single_515080`，平均波动、平均回撤、平均换手也略低，并在 10/17 个配置里拿到最高 Sharpe。但这个结论只来自 `2023-12-14` 之后的短共同历史，不能消除样本短的问题。

`split_515080_563020` 不建议作为默认替换方案。它在 10/17 个配置里最大回撤最浅，说明拆分两个红利 ETF 有一定平滑作用；但它在年化收益和 Sharpe 上 0/17 胜出，平均 Sharpe 只有 2.335，低于两个单资产方案，同时订单均值和拒单均值明显更高。它更像降低回撤的保守执行方案，不是提高组合质量的主方案。

## 建议

默认建议使用 `single_515080` 替换多数配置里的 `512890` 红利袖子。理由是跨配置收益胜率最高、执行拒单更少，而且 `515080` 的历史从 `2019-12-27` 开始，正式研究可用历史明显长于 `563020`。

如果目标是更低波动和更高短窗口 Sharpe，可以把 `single_563020` 作为观察方案，但不建议直接提交为正式基准红利袖子。`563020` 的共同样本只有从 `2023-12-14` 开始，无法满足到 `2025-06-30` 超过 3 年共同历史的正式输出条件。

不建议默认同时使用 `515080+563020`。除非你的实际约束是必须保留两个现有持仓并优先压低回撤，否则拆分红利袖子会牺牲收益和 Sharpe，并增加订单与拒单压力。
