# 平台实验报告：r049_value_training_v3_dynamic_participation

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\qcy_project\strategy\platform\results\temporary_backtests\experiments\r049_value_training_v3_dynamic_participation\20260725_061724\industry_value_rotation\r9_value_rotation_industry_dynamic_participation_candidate_20260725_061724_847819`
- 候选配置：`D:\qcy_project\strategy\platform\configs\r9_value_rotation_industry.yaml`
- Baseline 原始结果路径：`D:\qcy_project\strategy\platform\results\temporary_backtests\experiments\r049_value_training_v3_dynamic_participation\20260725_061724\monthly_equal_weight\domestic_industry_equal_weight_dynamic_participation_baseline_20260725_061727_155391`
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
- 累计收益率：58.64%
- 年化收益率：9.49%
- 年化波动率：21.59%
- 最大回撤：-29.92%
- Sharpe：0.4395
- 年化金额换手率：89.74%
- 成交笔数：103
- 订单数：105
- 拒单数：2
- 最大待执行意图数：7
- 平均现金权重：0.30%

## 候选训练样本指标
- 开始日期：2020-03-16
- 结束日期：2025-06-30
- 观测数：1283
- 累计收益率：58.64%
- 年化收益率：9.49%
- 年化波动率：21.59%
- 最大回撤：-29.92%
- Sharpe：0.4395
- 年化金额换手率：89.74%
- 成交笔数：103
- 订单数：105
- 拒单数：2
- 最大待执行意图数：7
- 平均现金权重：0.30%

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

## 候选执行拒单
- `limit_up`: 2

## Baseline 对比
- 累计收益率差值：0.1827
- 年化收益率差值：0.0260
- 年化波动率差值：0.0117
- 最大回撤差值：0.0636
- 夏普比率差值：0.1022
- 成交金额合计差值：8544692.0331
- 金额换手率差值：2.8436
- 年化金额换手率差值：0.5585
- 成交数量合计差值：9433000.0000
- 年化数量换手差值：926389.7116
- 成交笔数差值：-788.0000
- 订单数差值：-790.0000
- 拒单数差值：-2.0000
- 跳过订单数差值：-12.0000
- 低于一手或现金不足跳过数差值：-12.0000
- 最大待执行意图数差值：-9.0000
- 平均现金权重差值：0.0016
- execution_slippage_delta：0.0000
- annualized_fee_drag_delta：-0.0003

## 训练样本对比
- 累计收益率差值：0.1827
- 年化收益率差值：0.0260
- 年化波动率差值：0.0117
- 最大回撤差值：0.0636
- 夏普比率差值：0.1022
- 成交金额合计差值：8544692.0331
- 金额换手率差值：2.8436
- 年化金额换手率差值：0.5585
- 成交数量合计差值：9433000.0000
- 年化数量换手差值：926389.7116
- 成交笔数差值：-788.0000
- 订单数差值：-790.0000
- 拒单数差值：-2.0000
- 跳过订单数差值：-12.0000
- 低于一手或现金不足跳过数差值：-12.0000
- 最大待执行意图数差值：-9.0000
- 平均现金权重差值：0.0016
- execution_slippage_delta：0.0000
- annualized_fee_drag_delta：-0.0003

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
