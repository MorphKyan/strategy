# 平台实验报告：style_cross_market_us_cross_market

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_us_cross_market\20260531_012732\risk_parity\platform_us_cross_market_candidate_20260531_012733`
- 候选配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\platform_us_cross_market.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.codex\worktrees\b6cc\strategy\platform\results\backtests\style_cross_market_us_cross_market\20260531_012732\risk_parity\platform_baseline_for_us_cross_market_baseline_20260531_012755`
- Baseline 配置：`C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\baseline_for_us_cross_market.yaml`

## 候选指标
- 累计收益率：57.73%
- 年化收益率：5.58%
- 年化波动率：5.70%
- 最大回撤：-15.59%
- 夏普比率：0.9782
- 年化换手：452963.1820
- 成交笔数：82
- 订单数：82
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：4.10%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0347
- 年化收益率差值：-0.0027
- 年化波动率差值：0.0220
- 最大回撤差值：-0.1122
- 夏普比率差值：-0.6906
- 年化换手差值：3436.6003
- 成交笔数差值：24.0000
- 订单数差值：24.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0169

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
