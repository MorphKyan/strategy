# 平台实验报告：etf_selection_20260531_000612_execopt_v2

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt_v2\20260531_005025\risk_parity\platform_basket_518880_510310_159980_159981_511260_candidate_20260531_005025`
- 候选配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510310_159980_159981_511260.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt_v2\20260531_005025\risk_parity\baseline_aligned_518880_510310_159980_159981_511260_baseline_20260531_005036`
- Baseline 配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\aligned_baselines\baseline_aligned_for_518880_510310_159980_159981_511260.yaml`

## 候选指标
- 累计收益率：28.33%
- 年化收益率：6.55%
- 年化波动率：4.10%
- 最大回撤：-3.51%
- 夏普比率：1.5958
- 年化换手：655161.8145
- 成交笔数：55
- 订单数：56
- 拒单数：1
- 最大待执行意图数：3
- 平均现金权重：4.46%
- 是否有样本外指标：否

## 候选执行拒单
- `suspended`: 1

## Baseline 对比
- 累计收益率差值：-0.0358
- 年化收益率差值：-0.0075
- 年化波动率差值：0.0104
- 最大回撤差值：-0.0017
- 夏普比率差值：-0.7842
- 年化换手差值：182240.4653
- 成交笔数差值：38.0000
- 订单数差值：39.0000
- 拒单数差值：1.0000
- 最大待执行意图数差值：1.0000
- 平均现金权重差值：0.0022

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
