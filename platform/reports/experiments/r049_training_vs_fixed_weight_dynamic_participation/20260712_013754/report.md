# 平台实验报告：r049_training_vs_fixed_weight_dynamic_participation

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\r049_training_vs_fixed_weight_dynamic_participation\20260712_013754\robust_ellipsoidal_online_portfolio_adaptive\r049_robust_ellipsoidal_online_portfolio_adaptive_dynamic_participation_candidate_20260712_013754_825341`
- 候选配置：`D:\strategy\platform\configs\r049_robust_ellipsoidal_online_portfolio_adaptive.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\r049_training_vs_fixed_weight_dynamic_participation\20260712_013754\fixed_weight_threshold\r8_permanent_real_fixed_weight_threshold_dynamic_participation_baseline_20260712_014112_666888`
- Baseline 配置：`D:\strategy\platform\configs\r8_permanent_real_fixed_weight_threshold.yaml`

## 样本切分
- 训练样本截至：`2025-06-30`
- 样本外起始：`2025-07-01`
- 候选是否有训练指标：是
- 候选是否有样本外指标：否
- Baseline 是否有训练指标：是
- Baseline 是否有样本外指标：否

## 候选全样本指标
- 开始日期：2019-01-18
- 结束日期：2025-06-30
- 观测数：1561
- 累计收益率：-19.47%
- 年化收益率：-3.44%
- 年化波动率：14.44%
- 最大回撤：-40.33%
- Sharpe：-0.2379
- 年化金额换手率：1954.61%
- 成交笔数：418
- 订单数：418
- 拒单数：0
- 最大待执行意图数：4
- 平均现金权重：0.37%

## 候选训练样本指标
- 开始日期：2019-01-18
- 结束日期：2025-06-30
- 观测数：1561
- 累计收益率：-19.47%
- 年化收益率：-3.44%
- 年化波动率：14.44%
- 最大回撤：-40.33%
- Sharpe：-0.2379
- 年化金额换手率：1954.61%
- 成交笔数：418
- 订单数：418
- 拒单数：0
- 最大待执行意图数：4
- 平均现金权重：0.37%

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
- 累计收益率差值：-1.0913
- 年化收益率差值：-0.1432
- 年化波动率差值：0.0510
- 最大回撤差值：-0.3081
- 夏普比率差值：-1.4022
- 成交金额合计差值：223844715.5350
- 金额换手率差值：120.4593
- 年化金额换手率差值：19.4464
- 成交数量合计差值：77278800.0000
- 年化数量换手差值：6237750.6726
- 成交笔数差值：394.0000
- 订单数差值：394.0000
- 拒单数差值：0.0000
- 跳过订单数差值：80.0000
- 低于一手或现金不足跳过数差值：80.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0001
- execution_slippage_delta：0.0012
- annualized_fee_drag_delta：0.0079

## 训练样本对比
- 累计收益率差值：-1.0913
- 年化收益率差值：-0.1432
- 年化波动率差值：0.0510
- 最大回撤差值：-0.3081
- 夏普比率差值：-1.4022
- 成交金额合计差值：223844715.5350
- 金额换手率差值：120.4593
- 年化金额换手率差值：19.4464
- 成交数量合计差值：77278800.0000
- 年化数量换手差值：6237750.6726
- 成交笔数差值：394.0000
- 订单数差值：394.0000
- 拒单数差值：0.0000
- 跳过订单数差值：80.0000
- 低于一手或现金不足跳过数差值：80.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0001
- execution_slippage_delta：0.0012
- annualized_fee_drag_delta：0.0079

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
