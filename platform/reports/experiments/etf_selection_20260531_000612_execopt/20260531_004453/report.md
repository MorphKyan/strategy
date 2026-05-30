# 平台实验报告：etf_selection_20260531_000612_execopt

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt\20260531_004453\risk_parity\platform_basket_518880_510300_159980_159985_511260_candidate_20260531_004453`
- 候选配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510300_159980_159985_511260.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt\20260531_004453\risk_parity\baseline_aligned_518880_510300_159980_159985_511260_baseline_20260531_004505`
- Baseline 配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\aligned_baselines\baseline_aligned_for_518880_510300_159980_159985_511260.yaml`

## 候选指标
- 累计收益率：31.47%
- 年化收益率：7.21%
- 年化波动率：3.87%
- 最大回撤：-3.62%
- 夏普比率：1.8608
- 年化换手：623520.5773
- 成交笔数：42
- 订单数：43
- 拒单数：1
- 最大待执行意图数：2
- 平均现金权重：4.37%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 1

## Baseline 对比
- 累计收益率差值：-0.0044
- 年化收益率差值：-0.0009
- 年化波动率差值：0.0081
- 最大回撤差值：-0.0029
- 夏普比率差值：-0.5192
- 年化换手差值：150603.1910
- 成交笔数差值：23.0000
- 订单数差值：20.0000
- 拒单数差值：-3.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0013

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
