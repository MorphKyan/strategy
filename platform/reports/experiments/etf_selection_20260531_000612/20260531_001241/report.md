# 平台实验报告：etf_selection_20260531_000612

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612\20260531_001241\risk_parity\platform_basket_518880_510310_159980_159981_511260_candidate_20260531_001241`
- 候选配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510310_159980_159981_511260.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612\20260531_001241\risk_parity\platform_risk_parity_baseline_20260531_001252`
- Baseline 配置：`D:\strategy\platform\configs\platform_risk_parity.yaml`

## 候选指标
- 累计收益率：28.38%
- 年化收益率：6.56%
- 年化波动率：4.19%
- 最大回撤：-3.54%
- 夏普比率：1.5656
- 年化换手：703491.1202
- 成交笔数：71
- 订单数：622
- 拒单数：551
- 最大待执行意图数：4
- 平均现金权重：3.59%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 519
- `suspended`: 32

## Baseline 对比
- 累计收益率差值：-0.3245
- 年化收益率差值：0.0073
- 年化波动率差值：0.0066
- 最大回撤差值：0.0083
- 夏普比率差值：-0.0851
- 年化换手差值：248918.6699
- 成交笔数差值：14.0000
- 订单数差值：-574.0000
- 拒单数差值：-588.0000
- 最大待执行意图数差值：2.0000
- 平均现金权重差值：0.0173

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
