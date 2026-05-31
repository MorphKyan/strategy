# 平台实验报告：style_cross_market_dividend_replace_hs300

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_dividend_replace_hs300\20260531_012443\risk_parity\platform_dividend_replace_hs300_candidate_20260531_012443`
- 候选配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\platform_dividend_replace_hs300.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_dividend_replace_hs300\20260531_012443\risk_parity\platform_baseline_for_dividend_replace_hs300_baseline_20260531_012505`
- Baseline 配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\baseline_for_dividend_replace_hs300.yaml`

## 候选指标
- 累计收益率：53.09%
- 年化收益率：5.20%
- 年化波动率：3.56%
- 最大回撤：-4.47%
- 夏普比率：1.4610
- 年化换手：427332.7012
- 成交笔数：55
- 订单数：56
- 拒单数：1
- 最大待执行意图数：2
- 平均现金权重：2.46%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 1

## Baseline 对比
- 累计收益率差值：-0.0811
- 年化收益率差值：-0.0065
- 年化波动率差值：0.0005
- 最大回撤差值：-0.0010
- 夏普比率差值：-0.2078
- 年化换手差值：-22193.8806
- 成交笔数差值：-3.0000
- 订单数差值：-2.0000
- 拒单数差值：1.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0005

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
