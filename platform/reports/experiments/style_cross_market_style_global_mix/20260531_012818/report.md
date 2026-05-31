# 平台实验报告：style_cross_market_style_global_mix

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_style_global_mix\20260531_012818\risk_parity\platform_style_global_mix_candidate_20260531_012818`
- 候选配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\platform_style_global_mix.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_style_global_mix\20260531_012818\risk_parity\platform_baseline_for_style_global_mix_baseline_20260531_012838`
- Baseline 配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\baseline_for_style_global_mix.yaml`

## 候选指标
- 累计收益率：50.72%
- 年化收益率：6.00%
- 年化波动率：5.63%
- 最大回撤：-11.71%
- 夏普比率：1.0667
- 年化换手：414643.5274
- 成交笔数：71
- 订单数：71
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：3.76%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0405
- 年化收益率差值：-0.0040
- 年化波动率差值：0.0221
- 最大回撤差值：-0.0824
- 夏普比率差值：-0.8090
- 年化换手差值：12061.5303
- 成交笔数差值：28.0000
- 订单数差值：28.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0130

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
