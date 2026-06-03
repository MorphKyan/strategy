# 平台实验报告：baseline_mvp_equal_weight_exp

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_mvp_equal_weight_exp\20260603_154427\risk_parity_lw_cov\baseline_mvp_equal_weight_candidate_20260603_154427`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_mvp_equal_weight_candidate.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_mvp_equal_weight_exp\20260603_154427\monthly_equal_weight\baseline_mvp_equal_weight_baseline_20260603_154431`
- Baseline 配置：`D:\strategy\platform\configs\baseline_mvp_equal_weight.yaml`

## 候选指标
- 累计收益率：25.17%
- 年化收益率：2.70%
- 年化波动率：1.81%
- 最大回撤：-3.04%
- 夏普比率：1.4896
- 年化换手：180423.9955
- 成交笔数：15
- 订单数：15
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：70.92%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.6895
- 年化收益率差值：-0.0549
- 年化波动率差值：-0.0474
- 最大回撤差值：0.0809
- 夏普比率差值：0.2403
- 年化换手差值：-137726.1148
- 成交笔数差值：-141.0000
- 订单数差值：-141.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.4754

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
