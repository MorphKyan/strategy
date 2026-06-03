# 平台实验报告：baseline_r3_global_nasdaq_all_weather_ewma_exp

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_r3_global_nasdaq_all_weather_ewma_exp\20260603_154659\risk_parity_lw_cov\baseline_r3_global_nasdaq_all_weather_ewma_candidate_20260603_154659`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_r3_global_nasdaq_all_weather_ewma_candidate.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_r3_global_nasdaq_all_weather_ewma_exp\20260603_154659\risk_parity_ewma\baseline_r3_global_nasdaq_all_weather_ewma_baseline_20260603_154711`
- Baseline 配置：`D:\strategy\platform\configs\baseline_r3_global_nasdaq_all_weather_ewma.yaml`

## 候选指标
- 累计收益率：26.10%
- 年化收益率：6.22%
- 年化波动率：3.07%
- 最大回撤：-2.39%
- 夏普比率：2.0237
- 年化换手：476580.3848
- 成交笔数：42
- 订单数：42
- 拒单数：0
- 最大待执行意图数：3
- 平均现金权重：37.38%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0123
- 年化收益率差值：-0.0027
- 年化波动率差值：-0.0069
- 最大回撤差值：0.0096
- 夏普比率差值：0.3006
- 年化换手差值：-298470.8508
- 成交笔数差值：-28.0000
- 订单数差值：-28.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0054

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
