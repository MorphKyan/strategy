# 平台实验报告：style_cross_market_refine_dividend_dax

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_refine_dividend_dax\20260531_013417\risk_parity\platform_refine_dividend_dax_candidate_20260531_013417`
- 候选配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_013145_style_cross_market_refine_platform\platform_refine_dividend_dax.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_refine_dividend_dax\20260531_013417\risk_parity\platform_baseline_for_refine_dividend_dax_baseline_20260531_013440`
- Baseline 配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_013145_style_cross_market_refine_platform\baseline_for_refine_dividend_dax.yaml`

## 候选指标
- 累计收益率：51.83%
- 年化收益率：5.10%
- 年化波动率：3.92%
- 最大回撤：-6.03%
- 夏普比率：1.3028
- 年化换手：458122.4338
- 成交笔数：73
- 订单数：73
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：2.65%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0937
- 年化收益率差值：-0.0075
- 年化波动率差值：0.0041
- 最大回撤差值：-0.0166
- 夏普比率差值：-0.3660
- 年化换手差值：8595.8520
- 成交笔数差值：15.0000
- 订单数差值：15.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0024

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
