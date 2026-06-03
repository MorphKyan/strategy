# 平台实验报告：fundamental_value_equal_weight

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`results\backtests\fundamental_value_equal_weight\20260602_235135\fundamental_value_equal_weight\fundamental_dividend_candidate_20260602_235135`
- 候选配置：`configs\generated\platform_research_dividend_fundamental.yaml`

## 候选指标
- 累计收益率：20.04%
- 年化收益率：2.23%
- 年化波动率：6.22%
- 最大回撤：-10.40%
- 夏普比率：0.3583
- 年化换手：143765.6140
- 成交笔数：98
- 订单数：98
- 拒单数：0
- 最大待执行意图数：1
- 平均现金权重：49.90%
- 是否有样本外指标：否

## Baseline 对比
- 本次未请求 baseline 对比。

## 建议
- 复核

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
