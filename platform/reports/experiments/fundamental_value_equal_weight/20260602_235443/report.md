# 平台实验报告：fundamental_value_equal_weight

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`results\backtests\fundamental_value_equal_weight\20260602_235443\fundamental_value_equal_weight\fundamental_baseline_candidate_20260602_235443`
- 候选配置：`configs\generated\platform_research_baseline_fundamental.yaml`

## 候选指标
- 累计收益率：42.12%
- 年化收益率：4.37%
- 年化波动率：8.39%
- 最大回撤：-15.42%
- 夏普比率：0.5203
- 年化换手：316990.5934
- 成交笔数：144
- 订单数：144
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：0.35%
- 是否有样本外指标：否

## Baseline 对比
- 本次未请求 baseline 对比。

## 建议
- 复核

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
