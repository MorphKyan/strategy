# 平台实验报告：style_cross_market_refine_dividend_nasdaq

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_refine_dividend_nasdaq\20260531_013330\risk_parity\platform_refine_dividend_nasdaq_candidate_20260531_013330`
- 候选配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_013145_style_cross_market_refine_platform\platform_refine_dividend_nasdaq.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_refine_dividend_nasdaq\20260531_013330\risk_parity\platform_baseline_for_refine_dividend_nasdaq_baseline_20260531_013354`
- Baseline 配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_013145_style_cross_market_refine_platform\baseline_for_refine_dividend_nasdaq.yaml`

## 候选指标
- 累计收益率：58.22%
- 年化收益率：5.62%
- 年化波动率：4.95%
- 最大回撤：-9.69%
- 夏普比率：1.1356
- 年化换手：504507.9311
- 成交笔数：84
- 订单数：84
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：2.58%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0298
- 年化收益率差值：-0.0024
- 年化波动率差值：0.0144
- 最大回撤差值：-0.0532
- 夏普比率差值：-0.5332
- 年化换手差值：54981.3493
- 成交笔数差值：26.0000
- 订单数差值：26.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0017

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
