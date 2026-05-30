# 平台实验报告：etf_selection_20260531_000612_execopt

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt\20260531_004517\risk_parity\platform_basket_518880_510300_159985_159981_511260_candidate_20260531_004517`
- 候选配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510300_159985_159981_511260.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt\20260531_004517\risk_parity\baseline_aligned_518880_510300_159985_159981_511260_baseline_20260531_004528`
- Baseline 配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\aligned_baselines\baseline_aligned_for_518880_510300_159985_159981_511260.yaml`

## 候选指标
- 累计收益率：28.19%
- 年化收益率：6.52%
- 年化波动率：3.42%
- 最大回撤：-2.97%
- 夏普比率：1.9049
- 年化换手：490400.9517
- 成交笔数：29
- 订单数：33
- 拒单数：4
- 最大待执行意图数：3
- 平均现金权重：4.71%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 4

## Baseline 对比
- 累计收益率差值：-0.0372
- 年化收益率差值：-0.0078
- 年化波动率差值：0.0036
- 最大回撤差值：0.0036
- 夏普比率差值：-0.4751
- 年化换手差值：17483.5654
- 成交笔数差值：10.0000
- 订单数差值：10.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：1.0000
- 平均现金权重差值：0.0047

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
