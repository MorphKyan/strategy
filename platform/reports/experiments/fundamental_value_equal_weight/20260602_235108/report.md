# 平台实验报告：fundamental_value_equal_weight

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\fundamental_value_equal_weight\20260602_235108\fundamental_value_equal_weight\platform_m3m4_candidate_20260602_235108`
- 候选配置：`D:\strategy\platform\configs\platform_m3m4.yaml`

## 候选指标
- 累计收益率：30.15%
- 年化收益率：14.58%
- 年化波动率：16.70%
- 最大回撤：-23.65%
- 夏普比率：0.8728
- 年化换手：495320.5325
- 成交笔数：25
- 订单数：25
- 拒单数：0
- 最大待执行意图数：1
- 平均现金权重：49.60%
- 是否有样本外指标：否

## Baseline 对比
- 本次未请求 baseline 对比。

## 建议
- 复核

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
