# 平台实验报告：etf_selection_20260531_000612_execopt

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt\20260531_004408\risk_parity\platform_basket_518880_510300_159980_159981_511260_candidate_20260531_004408`
- 候选配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510300_159980_159981_511260.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt\20260531_004408\risk_parity\baseline_aligned_518880_510300_159980_159981_511260_baseline_20260531_004419`
- Baseline 配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\aligned_baselines\baseline_aligned_for_518880_510300_159980_159981_511260.yaml`

## 候选指标
- 累计收益率：28.56%
- 年化收益率：6.60%
- 年化波动率：4.09%
- 最大回撤：-3.53%
- 夏普比率：1.6123
- 年化换手：643689.4787
- 成交笔数：44
- 订单数：50
- 拒单数：6
- 最大待执行意图数：3
- 平均现金权重：4.65%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 6

## Baseline 对比
- 累计收益率差值：-0.0335
- 年化收益率差值：-0.0070
- 年化波动率差值：0.0103
- 最大回撤差值：-0.0020
- 夏普比率差值：-0.7676
- 年化换手差值：170772.0924
- 成交笔数差值：25.0000
- 订单数差值：27.0000
- 拒单数差值：2.0000
- 最大待执行意图数差值：1.0000
- 平均现金权重差值：0.0041

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
