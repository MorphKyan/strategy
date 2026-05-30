# 平台实验报告：etf_selection_20260531_000612_aligned

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_aligned\20260531_001705\risk_parity\platform_basket_518880_510300_159985_159981_511260_candidate_20260531_001705`
- 候选配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510300_159985_159981_511260.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_aligned\20260531_001705\risk_parity\baseline_aligned_518880_510300_159985_159981_511260_baseline_20260531_001716`
- Baseline 配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\aligned_baselines\baseline_aligned_for_518880_510300_159985_159981_511260.yaml`

## 候选指标
- 累计收益率：27.77%
- 年化收益率：6.43%
- 年化波动率：3.47%
- 最大回撤：-2.84%
- 夏普比率：1.8540
- 年化换手：557111.6627
- 成交笔数：43
- 订单数：554
- 拒单数：511
- 最大待执行意图数：4
- 平均现金权重：3.57%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 511

## Baseline 对比
- 累计收益率差值：-0.0478
- 年化收益率差值：-0.0100
- 年化波动率差值：0.0040
- 最大回撤差值：0.0042
- 夏普比率差值：-0.5661
- 年化换手差值：78496.8256
- 成交笔数差值：15.0000
- 订单数差值：195.0000
- 拒单数差值：180.0000
- 最大待执行意图数差值：2.0000
- 平均现金权重差值：0.0029

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
