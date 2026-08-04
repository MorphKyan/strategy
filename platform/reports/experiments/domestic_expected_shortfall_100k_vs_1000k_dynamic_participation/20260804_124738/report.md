# 平台实验报告：domestic_expected_shortfall_100k_vs_1000k_dynamic_participation

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\temporary_backtests\experiments\domestic_expected_shortfall_100k_vs_1000k_dynamic_participation\20260804_124738\risk_parity_expected_shortfall_fixed_budget\domestic_dividend_commodity_expected_shortfall_fixed_budget_bond_30y_511090_capital_100k_dynamic_participation_candidate_20260804_124738_601538`
- 候选配置：`D:\strategy\platform\configs\capital_100k\domestic_dividend_commodity_expected_shortfall_fixed_budget_bond_30y_511090.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\temporary_backtests\experiments\domestic_expected_shortfall_100k_vs_1000k_dynamic_participation\20260804_124738\risk_parity_expected_shortfall_fixed_budget\domestic_dividend_commodity_expected_shortfall_fixed_budget_bond_30y_511090_dynamic_participation_baseline_20260804_124748_067992`
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
- 累计收益率：28.52%
- 年化收益率：1.85%
- 年化波动率：2.93%
- 最大回撤：-6.12%
- Sharpe：0.6318
- 年化金额换手率：16.82%
- 成交笔数：122
- 订单数：123
- 拒单数：1
- 最大待执行意图数：6
- 平均现金权重：81.85%

## 候选训练样本指标
- 开始日期：2012-05-28
- 结束日期：2025-06-30
- 观测数：3181
- 累计收益率：21.56%
- 年化收益率：1.56%
- 年化波动率：2.49%
- 最大回撤：-6.12%
- Sharpe：0.6265
- 年化金额换手率：12.32%
- 成交笔数：65
- 订单数：65
- 拒单数：0
- 最大待执行意图数：6
- 平均现金权重：88.44%

## 候选样本外指标
- 开始日期：2025-07-01
- 结束日期：2026-08-04
- 观测数：267
- 累计收益率：5.42%
- 年化收益率：5.11%
- 年化波动率：6.10%
- 最大回撤：-3.83%
- Sharpe：0.8366
- 年化金额换手率：60.38%
- 成交笔数：57
- 订单数：58
- 拒单数：1
- 最大待执行意图数：6
- 平均现金权重：3.28%

## 候选执行拒单
- `limit_down`: 1

## Baseline 对比
- 累计收益率差值：-0.0072
- 年化收益率差值：-0.0004
- 年化波动率差值：-0.0004
- 最大回撤差值：0.0027
- 夏普比率差值：-0.0064
- 成交金额合计差值：-4333833.1358
- 金额换手率差值：-0.0259
- 年化金额换手率差值：-0.0019
- 成交数量合计差值：-1181100.0000
- 年化数量换手差值：-43160.8469
- 成交笔数差值：15.0000
- 订单数差值：15.0000
- 拒单数差值：0.0000
- 跳过订单数差值：10.0000
- 低于一手或现金不足跳过数差值：10.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0039
- execution_slippage_delta：-0.0000
- annualized_fee_drag_delta：0.0004

## 训练样本对比
- 累计收益率差值：-0.0052
- 年化收益率差值：-0.0003
- 年化波动率差值：-0.0001
- 最大回撤差值：0.0027
- 夏普比率差值：-0.0124
- 成交金额合计差值：-2878214.0398
- 金额换手率差值：-0.0187
- 年化金额换手率差值：-0.0015
- 成交数量合计差值：-791200.0000
- 年化数量换手差值：-31339.5787
- 成交笔数差值：5.0000
- 订单数差值：5.0000
- 拒单数差值：0.0000
- 跳过订单数差值：6.0000
- 低于一手或现金不足跳过数差值：6.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0016
- execution_slippage_delta：-0.0000
- annualized_fee_drag_delta：0.0002

## 样本外对比
- 累计收益率差值：-0.0014
- 年化收益率差值：-0.0013
- 年化波动率差值：-0.0020
- 最大回撤差值：0.0006
- 夏普比率差值：0.0056
- 成交金额合计差值：-1455619.0960
- 金额换手率差值：-0.0047
- 年化金额换手率差值：-0.0044
- 成交数量合计差值：-389900.0000
- 年化数量换手差值：-183997.7528
- 成交笔数差值：10.0000
- 订单数差值：10.0000
- 拒单数差值：0.0000
- 跳过订单数差值：4.0000
- 低于一手或现金不足跳过数差值：4.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0313
- execution_slippage_delta：-0.0000
- annualized_fee_drag_delta：0.0019

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
