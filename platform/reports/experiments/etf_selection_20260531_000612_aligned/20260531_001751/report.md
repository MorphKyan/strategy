# 平台实验报告：etf_selection_20260531_000612_aligned

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_aligned\20260531_001751\risk_parity\platform_basket_518880_510310_159980_159985_159981_511260_candidate_20260531_001751`
- 候选配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510310_159980_159985_159981_511260.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\etf_selection_20260531_000612_aligned\20260531_001751\risk_parity\baseline_aligned_518880_510310_159980_159985_159981_511260_baseline_20260531_001803`
- Baseline 配置：`D:\strategy\etf_selection\generated_configs\20260531_000612\aligned_baselines\baseline_aligned_for_518880_510310_159980_159985_159981_511260.yaml`

## 候选指标
- 累计收益率：29.01%
- 年化收益率：6.69%
- 年化波动率：4.16%
- 最大回撤：-3.63%
- 夏普比率：1.6090
- 年化换手：643864.5099
- 成交笔数：59
- 订单数：910
- 拒单数：851
- 最大待执行意图数：4
- 平均现金权重：3.51%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 819
- `suspended`: 32

## Baseline 对比
- 累计收益率差值：-0.0354
- 年化收益率差值：-0.0074
- 年化波动率差值：0.0109
- 最大回撤差值：-0.0037
- 夏普比率差值：-0.8111
- 年化换手差值：165249.6728
- 成交笔数差值：31.0000
- 订单数差值：551.0000
- 拒单数差值：520.0000
- 最大待执行意图数差值：2.0000
- 平均现金权重差值：0.0023

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
