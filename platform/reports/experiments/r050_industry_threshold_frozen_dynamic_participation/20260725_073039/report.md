# 平台实验报告：r050_industry_threshold_frozen_dynamic_participation

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\qcy_project\strategy\platform\results\temporary_backtests\experiments\r050_industry_threshold_frozen_dynamic_participation\20260725_073039\fixed_weight_threshold\r9_industry_equal_weight_threshold_dynamic_participation_candidate_20260725_073039_851060`
- 候选配置：`D:\qcy_project\strategy\platform\configs\r9_industry_equal_weight_threshold.yaml`
- Baseline 原始结果路径：`D:\qcy_project\strategy\platform\results\temporary_backtests\experiments\r050_industry_threshold_frozen_dynamic_participation\20260725_073039\monthly_equal_weight\domestic_industry_equal_weight_dynamic_participation_baseline_20260725_073040_890531`
- Baseline 配置：`D:\qcy_project\strategy\platform\configs\domestic_industry_equal_weight.yaml`

## 样本切分
- 训练样本截至：`2025-06-30`
- 样本外起始：`2025-07-01`
- 候选是否有训练指标：否
- 候选是否有样本外指标：是
- Baseline 是否有训练指标：否
- Baseline 是否有样本外指标：是

## 候选全样本指标
- 开始日期：2025-07-01
- 结束日期：2026-07-24
- 观测数：260
- 累计收益率：20.06%
- 年化收益率：19.39%
- 年化波动率：18.43%
- 最大回撤：-11.66%
- Sharpe：1.0521
- 年化金额换手率：67.29%
- 成交笔数：123
- 订单数：123
- 拒单数：0
- 最大待执行意图数：16
- 平均现金权重：0.41%

## 候选训练样本指标
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

## 候选样本外指标
- 开始日期：2025-07-01
- 结束日期：2026-07-24
- 观测数：260
- 累计收益率：20.06%
- 年化收益率：19.39%
- 年化波动率：18.43%
- 最大回撤：-11.66%
- Sharpe：1.0521
- 年化金额换手率：67.29%
- 成交笔数：123
- 订单数：123
- 拒单数：0
- 最大待执行意图数：16
- 平均现金权重：0.41%

## Baseline 对比
- 累计收益率差值：-0.0043
- 年化收益率差值：-0.0042
- 年化波动率差值：0.0007
- 最大回撤差值：-0.0056
- 夏普比率差值：-0.0264
- 成交金额合计差值：-184344.1268
- 金额换手率差值：-0.0761
- 年化金额换手率差值：-0.0738
- 成交数量合计差值：-197000.0000
- 年化数量换手差值：-95469.2308
- 成交笔数差值：-64.0000
- 订单数差值：-65.0000
- 拒单数差值：-1.0000
- 跳过订单数差值：-2.0000
- 低于一手或现金不足跳过数差值：-2.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：-0.0000
- execution_slippage_delta：0.0000
- annualized_fee_drag_delta：-0.0003

## 训练样本对比
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

## 样本外对比
- 累计收益率差值：-0.0043
- 年化收益率差值：-0.0042
- 年化波动率差值：0.0007
- 最大回撤差值：-0.0056
- 夏普比率差值：-0.0264
- 成交金额合计差值：-184344.1268
- 金额换手率差值：-0.0761
- 年化金额换手率差值：-0.0738
- 成交数量合计差值：-197000.0000
- 年化数量换手差值：-95469.2308
- 成交笔数差值：-64.0000
- 订单数差值：-65.0000
- 拒单数差值：-1.0000
- 跳过订单数差值：-2.0000
- 低于一手或现金不足跳过数差值：-2.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：-0.0000
- execution_slippage_delta：0.0000
- annualized_fee_drag_delta：-0.0003

## 建议
- 继续改进：缺少训练样本指标

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
