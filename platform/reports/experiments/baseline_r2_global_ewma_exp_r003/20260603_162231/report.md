# 平台实验报告：baseline_r2_global_ewma_exp_r003

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_r2_global_ewma_exp_r003\20260603_162231\risk_parity_dynamic_budget\baseline_r2_global_ewma_candidate_20260603_162231`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_r2_global_ewma_candidate_r003.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_r2_global_ewma_exp_r003\20260603_162231\risk_parity_ewma\baseline_r2_global_ewma_baseline_20260603_162253`
- Baseline 配置：`D:\strategy\platform\configs\baseline_r2_global_ewma.yaml`

## 候选指标
- 累计收益率：23.77%
- 年化收益率：3.10%
- 年化波动率：2.82%
- 最大回撤：-5.08%
- 夏普比率：1.1017
- 年化换手：222932.3880
- 成交笔数：18
- 订单数：18
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：70.87%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0857
- 年化收益率差值：-0.0099
- 年化波动率差值：0.0003
- 最大回撤差值：-0.0090
- 夏普比率差值：-0.3658
- 年化换手差值：-217153.2622
- 成交笔数差值：-29.0000
- 订单数差值：-29.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：-1.0000
- 平均现金权重差值：0.0569

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
