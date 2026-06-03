# 平台实验报告：baseline_r3_global_nasdaq_all_weather_ewma_exp_r003

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_r3_global_nasdaq_all_weather_ewma_exp_r003\20260603_162359\risk_parity_dynamic_budget\baseline_r3_global_nasdaq_all_weather_ewma_candidate_20260603_162359`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_r3_global_nasdaq_all_weather_ewma_candidate_r003.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_r3_global_nasdaq_all_weather_ewma_exp_r003\20260603_162359\risk_parity_ewma\baseline_r3_global_nasdaq_all_weather_ewma_baseline_20260603_162412`
- Baseline 配置：`D:\strategy\platform\configs\baseline_r3_global_nasdaq_all_weather_ewma.yaml`

## 候选指标
- 累计收益率：22.77%
- 年化收益率：5.48%
- 年化波动率：3.57%
- 最大回撤：-2.58%
- 夏普比率：1.5364
- 年化换手：439633.2673
- 成交笔数：29
- 订单数：29
- 拒单数：0
- 最大待执行意图数：3
- 平均现金权重：47.73%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0663
- 年化收益率差值：-0.0145
- 年化波动率差值：-0.0049
- 最大回撤差值：0.0080
- 夏普比率差值：-0.1704
- 年化换手差值：-423687.0514
- 成交笔数差值：-35.0000
- 订单数差值：-35.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：-2.0000
- 平均现金权重差值：0.1082

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
