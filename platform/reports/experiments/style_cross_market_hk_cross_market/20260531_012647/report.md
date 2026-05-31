# 平台实验报告：style_cross_market_hk_cross_market

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_hk_cross_market\20260531_012647\risk_parity\platform_hk_cross_market_candidate_20260531_012647`
- 候选配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\platform_hk_cross_market.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_hk_cross_market\20260531_012647\risk_parity\platform_baseline_for_hk_cross_market_baseline_20260531_012709`
- Baseline 配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\baseline_for_hk_cross_market.yaml`

## 候选指标
- 累计收益率：55.72%
- 年化收益率：5.42%
- 年化波动率：4.02%
- 最大回撤：-6.41%
- 夏普比率：1.3483
- 年化换手：488444.3456
- 成交笔数：83
- 订单数：83
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：2.65%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0548
- 年化收益率差值：-0.0044
- 年化波动率差值：0.0051
- 最大回撤差值：-0.0204
- 夏普比率差值：-0.3205
- 年化换手差值：38917.7638
- 成交笔数差值：25.0000
- 订单数差值：25.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0024

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
