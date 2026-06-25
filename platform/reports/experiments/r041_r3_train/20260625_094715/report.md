# 平台实验报告：r041_r3_train

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\r041_r3_train\20260625_094715\risk_parity_min_torsion_enb\r041_min_torsion_enb_r3_global_nasdaq_all_weather_ewma_candidate_20260625_094715_670542`
- 候选配置：`D:\strategy\platform\configs\r041_min_torsion_enb_r3_global_nasdaq_all_weather_ewma.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\r041_r3_train\20260625_094715\risk_parity_lw_cov\baseline_r3_global_nasdaq_all_weather_ewma_baseline_20260625_094716_845338`
- Baseline 配置：`D:\strategy\platform\configs\baseline_r3_global_nasdaq_all_weather_ewma.yaml`

## 候选指标
- 累计收益率：103.73%
- 年化收益率：14.58%
- 年化波动率：21.73%
- 最大回撤：-27.01%
- 夏普比率：0.6706
- 成交金额合计：11481383.0019
- 金额换手率：397.44%
- 年化金额换手率：75.99%
- 成交数量合计：4496600.0000
- 年化数量换手：429872.2307
- 成交笔数：248
- 订单数：248
- 拒单数：0
- 跳过订单数：17
- 低于一手或现金不足跳过数：17
- 最大待执行意图数：7
- 平均现金权重：2.68%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：0.0148
- 年化收益率差值：0.0016
- 年化波动率差值：0.0001
- 最大回撤差值：-0.0004
- 夏普比率差值：0.0069
- 成交金额合计差值：-321546.1937
- 金额换手率差值：-0.1758
- 年化金额换手率差值：-0.0336
- 成交数量合计差值：74800.0000
- 年化数量换手差值：7150.8346
- 成交笔数差值：-21.0000
- 订单数差值：-21.0000
- 拒单数差值：0.0000
- 跳过订单数差值：0.0000
- 低于一手或现金不足跳过数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：-0.0002

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
