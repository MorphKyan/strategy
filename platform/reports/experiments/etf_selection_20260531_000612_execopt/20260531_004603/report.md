# 平台实验报告：etf_selection_20260531_000612_execopt

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt\20260531_004603\risk_parity\platform_basket_518880_510310_159980_159985_159981_511260_candidate_20260531_004603`
- 候选配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510310_159980_159985_159981_511260.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_execopt\20260531_004603\risk_parity\baseline_aligned_518880_510310_159980_159985_159981_511260_baseline_20260531_004614`
- Baseline 配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\aligned_baselines\baseline_aligned_for_518880_510310_159980_159985_159981_511260.yaml`

## 候选指标
- 累计收益率：28.68%
- 年化收益率：6.62%
- 年化波动率：4.14%
- 最大回撤：-3.78%
- 夏普比率：1.5978
- 年化换手：635800.8984
- 成交笔数：54
- 订单数：64
- 拒单数：10
- 最大待执行意图数：3
- 平均现金权重：4.35%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 7
- `suspended`: 3

## Baseline 对比
- 累计收益率差值：-0.0323
- 年化收益率差值：-0.0067
- 年化波动率差值：0.0108
- 最大回撤差值：-0.0045
- 夏普比率差值：-0.7821
- 年化换手差值：162883.5121
- 成交笔数差值：35.0000
- 订单数差值：41.0000
- 拒单数差值：6.0000
- 最大待执行意图数差值：1.0000
- 平均现金权重差值：0.0011

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
