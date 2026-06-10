# 平台实验报告：monthly_equal_weight

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\monthly_equal_weight\20260610_173819\monthly_equal_weight\baseline_r0_domestic_equal_weight_candidate_20260610_173819_289249`
- 候选配置：`D:\strategy\platform\configs\baseline_r0_domestic_equal_weight.yaml`

## 候选指标
- 累计收益率：98.20%
- 年化收益率：8.42%
- 年化波动率：8.56%
- 最大回撤：-11.16%
- 夏普比率：0.9838
- 成交金额合计：3939337.9842
- 金额换手率：147.81%
- 年化金额换手率：17.47%
- 成交数量合计：751600.0000
- 年化数量换手：44419.1370
- 成交笔数：223
- 订单数：224
- 拒单数：1
- 最大待执行意图数：3
- 平均现金权重：0.27%
- 是否有样本外指标：否

## 候选执行拒单
- `limit_down`: 1

## Baseline 对比
- 本次未请求 baseline 对比。

## 建议
- 复核

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
