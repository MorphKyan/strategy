# 平台实验报告：domestic_expected_shortfall_100k_vs_1000k_stress

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\temporary_backtests\experiments\domestic_expected_shortfall_100k_vs_1000k_stress\20260804_124717\risk_parity_expected_shortfall_fixed_budget\domestic_dividend_commodity_expected_shortfall_fixed_budget_bond_30y_511090_capital_100k_stress_candidate_20260804_124717_870559`
- 候选配置：`D:\strategy\platform\configs\capital_100k\domestic_dividend_commodity_expected_shortfall_fixed_budget_bond_30y_511090.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\temporary_backtests\experiments\domestic_expected_shortfall_100k_vs_1000k_stress\20260804_124717\risk_parity_expected_shortfall_fixed_budget\domestic_dividend_commodity_expected_shortfall_fixed_budget_bond_30y_511090_stress_baseline_20260804_124728_880429`
- Baseline 配置：`D:\strategy\platform\configs\domestic_dividend_commodity_expected_shortfall_fixed_budget_bond_30y_511090.yaml`

## 样本切分
- 训练样本截至：`2025-06-30`
- 样本外起始：`2025-07-01`
- 候选是否有训练指标：是
- 候选是否有样本外指标：是
- Baseline 是否有训练指标：是
- Baseline 是否有样本外指标：是

## 候选全样本指标
- 开始日期：2012-05-28
- 结束日期：2026-08-04
- 观测数：3448
- 累计收益率：27.86%
- 年化收益率：1.81%
- 年化波动率：2.93%
- 最大回撤：-6.15%
- Sharpe：0.6188
- 年化金额换手率：16.90%
- 成交笔数：124
- 订单数：125
- 拒单数：1
- 最大待执行意图数：6
- 平均现金权重：81.86%

## 候选训练样本指标
- 开始日期：2012-05-28
- 结束日期：2025-06-30
- 观测数：3181
- 累计收益率：21.04%
- 年化收益率：1.52%
- 年化波动率：2.48%
- 最大回撤：-6.15%
- Sharpe：0.6139
- 年化金额换手率：12.39%
- 成交笔数：65
- 订单数：65
- 拒单数：0
- 最大待执行意图数：6
- 平均现金权重：88.42%

## 候选样本外指标
- 开始日期：2025-07-01
- 结束日期：2026-08-04
- 观测数：267
- 累计收益率：5.32%
- 年化收益率：5.02%
- 年化波动率：6.12%
- 最大回撤：-3.88%
- Sharpe：0.8195
- 年化金额换手率：60.74%
- 成交笔数：59
- 订单数：60
- 拒单数：1
- 最大待执行意图数：6
- 平均现金权重：3.71%

## 候选执行拒单
- `limit_down`: 1

## Baseline 对比
- 累计收益率差值：-0.0075
- 年化收益率差值：-0.0004
- 年化波动率差值：-0.0004
- 最大回撤差值：0.0030
- 夏普比率差值：-0.0072
- 成交金额合计差值：-4361107.3543
- 金额换手率差值：-0.0307
- 年化金额换手率差值：-0.0022
- 成交数量合计差值：-1184800.0000
- 年化数量换手差值：-43296.0557
- 成交笔数差值：12.0000
- 订单数差值：12.0000
- 拒单数差值：0.0000
- 跳过订单数差值：10.0000
- 低于一手或现金不足跳过数差值：10.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0040
- execution_slippage_delta：-0.0000
- annualized_fee_drag_delta：0.0004

## 训练样本对比
- 累计收益率差值：-0.0062
- 年化收益率差值：-0.0004
- 年化波动率差值：-0.0001
- 最大回撤差值：0.0030
- 夏普比率差值：-0.0136
- 成交金额合计差值：-2897763.3116
- 金额换手率差值：-0.0211
- 年化金额换手率差值：-0.0017
- 成交数量合计差值：-790500.0000
- 年化数量换手差值：-31311.8516
- 成交笔数差值：3.0000
- 订单数差值：3.0000
- 拒单数差值：0.0000
- 跳过订单数差值：7.0000
- 低于一手或现金不足跳过数差值：7.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0013
- execution_slippage_delta：-0.0001
- annualized_fee_drag_delta：0.0002

## 样本外对比
- 累计收益率差值：-0.0008
- 年化收益率差值：-0.0007
- 年化波动率差值：-0.0017
- 最大回撤差值：0.0002
- 夏普比率差值：0.0106
- 成交金额合计差值：-1463344.0427
- 金额换手率差值：-0.0066
- 年化金额换手率差值：-0.0062
- 成交数量合计差值：-394300.0000
- 年化数量换手差值：-186074.1573
- 成交笔数差值：9.0000
- 订单数差值：9.0000
- 拒单数差值：0.0000
- 跳过订单数差值：3.0000
- 低于一手或现金不足跳过数差值：3.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0350
- execution_slippage_delta：-0.0000
- annualized_fee_drag_delta：0.0019

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
