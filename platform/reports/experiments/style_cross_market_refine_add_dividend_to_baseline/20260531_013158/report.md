# 平台实验报告：style_cross_market_refine_add_dividend_to_baseline

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_refine_add_dividend_to_baseline\20260531_013158\risk_parity\platform_refine_add_dividend_to_baseline_candidate_20260531_013158`
- 候选配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_013145_style_cross_market_refine_platform\platform_refine_add_dividend_to_baseline.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_refine_add_dividend_to_baseline\20260531_013158\risk_parity\platform_baseline_for_refine_add_dividend_to_baseline_baseline_20260531_013221`
- Baseline 配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_013145_style_cross_market_refine_platform\baseline_for_refine_add_dividend_to_baseline.yaml`

## 候选指标
- 累计收益率：53.33%
- 年化收益率：5.22%
- 年化波动率：4.06%
- 最大回撤：-7.54%
- 夏普比率：1.2875
- 年化换手：450938.1415
- 成交笔数：73
- 订单数：73
- 拒单数：0
- 最大待执行意图数：3
- 平均现金权重：2.45%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0787
- 年化收益率差值：-0.0063
- 年化波动率差值：0.0055
- 最大回撤差值：-0.0317
- 夏普比率差值：-0.3813
- 年化换手差值：1411.5598
- 成交笔数差值：15.0000
- 订单数差值：15.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：1.0000
- 平均现金权重差值：0.0003

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
