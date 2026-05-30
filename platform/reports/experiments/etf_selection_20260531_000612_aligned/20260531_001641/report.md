# 平台实验报告：etf_selection_20260531_000612_aligned

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_aligned\20260531_001641\risk_parity\platform_basket_518880_510300_159980_159985_511260_candidate_20260531_001641`
- 候选配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510300_159980_159985_511260.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_aligned\20260531_001641\risk_parity\baseline_aligned_518880_510300_159980_159985_511260_baseline_20260531_001653`
- Baseline 配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\aligned_baselines\baseline_aligned_for_518880_510300_159980_159985_511260.yaml`

## 候选指标
- 累计收益率：32.14%
- 年化收益率：7.34%
- 年化波动率：3.86%
- 最大回撤：-3.58%
- 夏普比率：1.9039
- 年化换手：638164.2449
- 成交笔数：52
- 订单数：721
- 拒单数：669
- 最大待执行意图数：4
- 平均现金权重：3.47%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 669

## Baseline 对比
- 累计收益率差值：-0.0041
- 年化收益率差值：-0.0008
- 年化波动率差值：0.0079
- 最大回撤差值：-0.0032
- 夏普比率差值：-0.5162
- 年化换手差值：159549.4077
- 成交笔数差值：24.0000
- 订单数差值：362.0000
- 拒单数差值：338.0000
- 最大待执行意图数差值：2.0000
- 平均现金权重差值：0.0020

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
