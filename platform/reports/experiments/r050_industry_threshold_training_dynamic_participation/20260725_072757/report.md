# 平台实验报告：r050_industry_threshold_training_dynamic_participation

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\qcy_project\strategy\platform\results\temporary_backtests\experiments\r050_industry_threshold_training_dynamic_participation\20260725_072757\fixed_weight_threshold\r9_industry_equal_weight_threshold_dynamic_participation_candidate_20260725_072757_256718`
- 候选配置：`D:\qcy_project\strategy\platform\configs\r9_industry_equal_weight_threshold.yaml`
- Baseline 原始结果路径：`D:\qcy_project\strategy\platform\results\temporary_backtests\experiments\r050_industry_threshold_training_dynamic_participation\20260725_072757\monthly_equal_weight\domestic_industry_equal_weight_dynamic_participation_baseline_20260725_072759_251698`
- Baseline 配置：`D:\qcy_project\strategy\platform\configs\domestic_industry_equal_weight.yaml`

## 样本切分
- 训练样本截至：`2025-06-30`
- 样本外起始：`2025-07-01`
- 候选是否有训练指标：是
- 候选是否有样本外指标：否
- Baseline 是否有训练指标：是
- Baseline 是否有样本外指标：否

## 候选全样本指标
- 开始日期：2020-03-16
- 结束日期：2025-06-30
- 观测数：1283
- 累计收益率：41.94%
- 年化收益率：7.12%
- 年化波动率：20.35%
- 最大回撤：-36.16%
- Sharpe：0.3499
- 年化金额换手率：25.20%
- 成交笔数：342
- 订单数：342
- 拒单数：0
- 最大待执行意图数：16
- 平均现金权重：0.22%

## 候选训练样本指标
- 开始日期：2020-03-16
- 结束日期：2025-06-30
- 观测数：1283
- 累计收益率：41.94%
- 年化收益率：7.12%
- 年化波动率：20.35%
- 最大回撤：-36.16%
- Sharpe：0.3499
- 年化金额换手率：25.20%
- 成交笔数：342
- 订单数：342
- 拒单数：0
- 最大待执行意图数：16
- 平均现金权重：0.22%

## 候选样本外指标
- 开始日期：None
- 结束日期：None
- 观测数：0
- 累计收益率：N/A
- 年化收益率：N/A
- 年化波动率：N/A
- 最大回撤：N/A
- Sharpe：N/A
- 年化金额换手率：0.00%
- 成交笔数：0
- 订单数：0
- 拒单数：0
- 最大待执行意图数：0
- 平均现金权重：N/A

## Baseline 对比
- 累计收益率差值：0.0157
- 年化收益率差值：0.0023
- 年化波动率差值：-0.0006
- 最大回撤差值：0.0012
- 夏普比率差值：0.0125
- 成交金额合计差值：-1161612.5814
- 金额换手率差值：-0.4419
- 年化金额换手率差值：-0.0868
- 成交数量合计差值：-1179200.0000
- 年化数量换手差值：-115806.0795
- 成交笔数差值：-549.0000
- 订单数差值：-553.0000
- 拒单数差值：-4.0000
- 跳过订单数差值：-9.0000
- 低于一手或现金不足跳过数差值：-9.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0007
- execution_slippage_delta：-0.0000
- annualized_fee_drag_delta：-0.0004

## 训练样本对比
- 累计收益率差值：0.0157
- 年化收益率差值：0.0023
- 年化波动率差值：-0.0006
- 最大回撤差值：0.0012
- 夏普比率差值：0.0125
- 成交金额合计差值：-1161612.5814
- 金额换手率差值：-0.4419
- 年化金额换手率差值：-0.0868
- 成交数量合计差值：-1179200.0000
- 年化数量换手差值：-115806.0795
- 成交笔数差值：-549.0000
- 订单数差值：-553.0000
- 拒单数差值：-4.0000
- 跳过订单数差值：-9.0000
- 低于一手或现金不足跳过数差值：-9.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0007
- execution_slippage_delta：-0.0000
- annualized_fee_drag_delta：-0.0004

## 样本外对比
- 累计收益率差值：N/A
- 年化收益率差值：N/A
- 年化波动率差值：N/A
- 最大回撤差值：N/A
- 夏普比率差值：N/A
- 成交金额合计差值：0.0000
- 金额换手率差值：0.0000
- 年化金额换手率差值：0.0000
- 成交数量合计差值：0.0000
- 年化数量换手差值：0.0000
- 成交笔数差值：0.0000
- 订单数差值：0.0000
- 拒单数差值：0.0000
- 跳过订单数差值：0.0000
- 低于一手或现金不足跳过数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：N/A
- execution_slippage_delta：0.0000
- annualized_fee_drag_delta：0.0000

## 建议
- 继续改进：缺少样本外指标

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
