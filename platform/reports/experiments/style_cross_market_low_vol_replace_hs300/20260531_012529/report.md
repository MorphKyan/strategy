# 平台实验报告：style_cross_market_low_vol_replace_hs300

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_low_vol_replace_hs300\20260531_012529\risk_parity\platform_low_vol_replace_hs300_candidate_20260531_012529`
- 候选配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\platform_low_vol_replace_hs300.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_low_vol_replace_hs300\20260531_012529\risk_parity\platform_baseline_for_low_vol_replace_hs300_baseline_20260531_012548`
- Baseline 配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\baseline_for_low_vol_replace_hs300.yaml`

## 候选指标
- 累计收益率：46.98%
- 年化收益率：5.63%
- 年化波动率：4.01%
- 最大回撤：-7.46%
- 夏普比率：1.4027
- 年化换手：361720.4911
- 成交笔数：41
- 订单数：41
- 拒单数：0
- 最大待执行意图数：3
- 平均现金权重：2.85%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0778
- 年化收益率差值：-0.0078
- 年化波动率差值：0.0060
- 最大回撤差值：-0.0399
- 夏普比率差值：-0.4729
- 年化换手差值：-40861.5060
- 成交笔数差值：-2.0000
- 订单数差值：-2.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：1.0000
- 平均现金权重差值：0.0040

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
