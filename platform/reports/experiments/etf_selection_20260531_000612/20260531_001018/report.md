# 平台实验报告：etf_selection_20260531_000612

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612\20260531_001018\risk_parity\platform_basket_518880_510300_159980_159981_511260_candidate_20260531_001018`
- 候选配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510300_159980_159981_511260.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612\20260531_001018\risk_parity\platform_risk_parity_baseline_20260531_001029`
- Baseline 配置：`D:\strategy\platform\configs\platform_risk_parity.yaml`

## 候选指标
- 累计收益率：28.72%
- 年化收益率：6.63%
- 年化波动率：4.20%
- 最大回撤：-3.56%
- 夏普比率：1.5805
- 年化换手：714594.0646
- 成交笔数：70
- 订单数：808
- 拒单数：738
- 最大待执行意图数：4
- 平均现金权重：3.44%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 738

## Baseline 对比
- 累计收益率差值：-0.3212
- 年化收益率差值：0.0081
- 年化波动率差值：0.0067
- 最大回撤差值：0.0081
- 夏普比率差值：-0.0702
- 年化换手差值：260021.6143
- 成交笔数差值：13.0000
- 订单数差值：-388.0000
- 拒单数差值：-401.0000
- 最大待执行意图数差值：2.0000
- 平均现金权重差值：0.0157

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
