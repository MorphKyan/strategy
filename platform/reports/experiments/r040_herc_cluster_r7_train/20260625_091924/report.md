# 平台实验报告：r040_herc_cluster_r7_train

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\r040_herc_cluster_r7_train\20260625_091924\herc_cluster_risk_parity\r040_herc_cluster_r7_cluster_representative_damped_3x_candidate_20260625_091924_958871`
- 候选配置：`D:\strategy\platform\configs\r040_herc_cluster_r7_cluster_representative_damped_3x.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\r040_herc_cluster_r7_train\20260625_091924\cluster_representative_damped_risk_parity\r040_baseline_r7_cluster_representative_damped_3x_baseline_20260625_091926_060215`
- Baseline 配置：`D:\strategy\platform\configs\r040_baseline_r7_cluster_representative_damped_3x.yaml`

## 候选指标
- 累计收益率：136.73%
- 年化收益率：17.91%
- 年化波动率：13.68%
- 最大回撤：-14.98%
- 夏普比率：1.3096
- 成交金额合计：5466438.1761
- 金额换手率：195.48%
- 年化金额换手率：37.37%
- 成交数量合计：1878700.0000
- 年化数量换手：179602.5797
- 成交笔数：93
- 订单数：93
- 拒单数：0
- 跳过订单数：7
- 低于一手或现金不足跳过数：7
- 最大待执行意图数：6
- 平均现金权重：2.66%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0659
- 年化收益率差值：-0.0062
- 年化波动率差值：-0.0060
- 最大回撤差值：-0.0081
- 夏普比率差值：0.0112
- 成交金额合计差值：-298520.4703
- 金额换手率差值：-0.1238
- 年化金额换手率差值：-0.0237
- 成交数量合计差值：75300.0000
- 年化数量换手差值：7198.6343
- 成交笔数差值：1.0000
- 订单数差值：1.0000
- 拒单数差值：0.0000
- 跳过订单数差值：0.0000
- 低于一手或现金不足跳过数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：-0.0023

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
