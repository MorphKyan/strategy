# 平台实验报告：etf_selection_20260531_000612_execopt_v2

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt_v2\20260531_005047\risk_parity\platform_basket_518880_510310_159980_159985_159981_511260_candidate_20260531_005048`
- 候选配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510310_159980_159985_159981_511260.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt_v2\20260531_005047\risk_parity\baseline_aligned_518880_510310_159980_159985_159981_511260_baseline_20260531_005059`
- Baseline 配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\aligned_baselines\baseline_aligned_for_518880_510310_159980_159985_159981_511260.yaml`

## 候选指标
- 累计收益率：28.54%
- 年化收益率：6.59%
- 年化波动率：4.11%
- 最大回撤：-3.77%
- 夏普比率：1.6045
- 年化换手：635520.5738
- 成交笔数：55
- 订单数：58
- 拒单数：3
- 最大待执行意图数：2
- 平均现金权重：4.43%
- 是否有样本外指标：否

## 候选执行拒单
- `suspended`: 3

## Baseline 对比
- 累计收益率差值：-0.0337
- 年化收益率差值：-0.0070
- 年化波动率差值：0.0104
- 最大回撤差值：-0.0044
- 夏普比率差值：-0.7755
- 年化换手差值：162599.2246
- 成交笔数差值：38.0000
- 订单数差值：41.0000
- 拒单数差值：3.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0019

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
