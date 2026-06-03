# 平台实验报告：fundamental_value_equal_weight

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`results\backtests\fundamental_value_equal_weight\20260602_235505\fundamental_value_equal_weight\fundamental_dividend_candidate_20260602_235505`
- 候选配置：`configs\generated\platform_research_dividend_fundamental.yaml`

## 候选指标
- 累计收益率：40.56%
- 年化收益率：4.19%
- 年化波动率：6.05%
- 最大回撤：-8.20%
- 夏普比率：0.6933
- 年化换手：224345.1171
- 成交笔数：104
- 订单数：107
- 拒单数：3
- 最大待执行意图数：2
- 平均现金权重：0.30%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 3

## Baseline 对比
- 本次未请求 baseline 对比。

## 建议
- 复核

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
