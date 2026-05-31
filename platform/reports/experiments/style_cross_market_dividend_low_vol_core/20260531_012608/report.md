# 平台实验报告：style_cross_market_dividend_low_vol_core

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_dividend_low_vol_core\20260531_012608\risk_parity\platform_dividend_low_vol_core_candidate_20260531_012608`
- 候选配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\platform_dividend_low_vol_core.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_dividend_low_vol_core\20260531_012608\risk_parity\platform_baseline_for_dividend_low_vol_core_baseline_20260531_012627`
- Baseline 配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\baseline_for_dividend_low_vol_core.yaml`

## 候选指标
- 累计收益率：47.31%
- 年化收益率：5.66%
- 年化波动率：4.55%
- 最大回撤：-8.54%
- 夏普比率：1.2438
- 年化换手：408714.9016
- 成交笔数：49
- 订单数：49
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：2.62%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0745
- 年化收益率差值：-0.0074
- 年化波动率差值：0.0114
- 最大回撤差值：-0.0507
- 夏普比率差值：-0.6319
- 年化换手差值：6132.9044
- 成交笔数差值：6.0000
- 订单数差值：6.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0016

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
