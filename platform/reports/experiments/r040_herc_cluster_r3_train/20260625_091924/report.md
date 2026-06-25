# 平台实验报告：r040_herc_cluster_r3_train

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\r040_herc_cluster_r3_train\20260625_091924\herc_cluster_risk_parity\r040_herc_cluster_r3_global_nasdaq_all_weather_ewma_candidate_20260625_091924_992164`
- 候选配置：`D:\strategy\platform\configs\r040_herc_cluster_r3_global_nasdaq_all_weather_ewma.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\r040_herc_cluster_r3_train\20260625_091924\risk_parity_lw_cov\baseline_r3_global_nasdaq_all_weather_ewma_baseline_20260625_091926_234763`
- Baseline 配置：`D:\strategy\platform\configs\baseline_r3_global_nasdaq_all_weather_ewma.yaml`

## 候选指标
- 累计收益率：102.87%
- 年化收益率：14.48%
- 年化波动率：24.83%
- 最大回撤：-31.11%
- 夏普比率：0.5833
- 成交金额合计：9706938.7117
- 金额换手率：346.58%
- 年化金额换手率：66.27%
- 成交数量合计：3558700.0000
- 年化数量换手：340209.5599
- 成交笔数：216
- 订单数：216
- 拒单数：0
- 跳过订单数：13
- 低于一手或现金不足跳过数：13
- 最大待执行意图数：7
- 平均现金权重：2.62%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：0.0061
- 年化收益率差值：0.0007
- 年化波动率差值：0.0311
- 最大回撤差值：-0.0414
- 夏普比率差值：-0.0804
- 成交金额合计差值：-2095990.4839
- 金额换手率差值：-0.6844
- 年化金额换手率差值：-0.1309
- 成交数量合计差值：-863100.0000
- 年化数量换手差值：-82511.8361
- 成交笔数差值：-53.0000
- 订单数差值：-53.0000
- 拒单数差值：0.0000
- 跳过订单数差值：-4.0000
- 低于一手或现金不足跳过数差值：-4.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：-0.0008

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
