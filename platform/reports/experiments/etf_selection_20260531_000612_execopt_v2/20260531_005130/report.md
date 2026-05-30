# 平台实验报告：etf_selection_20260531_000612_execopt_v2

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt_v2\20260531_005130\risk_parity\platform_basket_518880_510310_159985_159981_511260_candidate_20260531_005131`
- 候选配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510310_159985_159981_511260.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt_v2\20260531_005130\risk_parity\baseline_aligned_518880_510310_159985_159981_511260_baseline_20260531_005141`
- Baseline 配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\aligned_baselines\baseline_aligned_for_518880_510310_159985_159981_511260.yaml`

## 候选指标
- 累计收益率：27.00%
- 年化收益率：6.27%
- 年化波动率：3.46%
- 最大回撤：-2.87%
- 夏普比率：1.8128
- 年化换手：548758.2219
- 成交笔数：32
- 订单数：64
- 拒单数：32
- 最大待执行意图数：3
- 平均现金权重：4.49%
- 是否有样本外指标：否

## 候选执行拒单
- `suspended`: 32

## Baseline 对比
- 累计收益率差值：-0.0491
- 年化收益率差值：-0.0103
- 年化波动率差值：0.0039
- 最大回撤差值：0.0046
- 夏普比率差值：-0.5672
- 年化换手差值：75836.8727
- 成交笔数差值：15.0000
- 订单数差值：47.0000
- 拒单数差值：32.0000
- 最大待执行意图数差值：1.0000
- 平均现金权重差值：0.0025

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
