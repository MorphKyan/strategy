# 平台实验报告：fundamental_value_equal_weight

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`results\backtests\fundamental_value_equal_weight\20260602_235237\fundamental_value_equal_weight\fundamental_baseline_candidate_20260602_235237`
- 候选配置：`configs\generated\platform_research_baseline_fundamental.yaml`

## 候选指标
- 累计收益率：N/A
- 年化收益率：N/A
- 年化波动率：N/A
- 最大回撤：N/A
- 夏普比率：N/A
- 年化换手：0.0000
- 成交笔数：0
- 订单数：0
- 拒单数：0
- 最大待执行意图数：0
- 平均现金权重：N/A
- 是否有样本外指标：否

## Baseline 对比
- 本次未请求 baseline 对比。

## 建议
- 复核

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
