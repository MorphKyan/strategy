# 平台实验报告：r041_us_blend_train

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\r041_us_blend_train\20260625_094715\risk_parity_min_torsion_enb\r041_min_torsion_enb_us_blend_ewma_candidate_20260625_094715_668192`
- 候选配置：`D:\strategy\platform\configs\r041_min_torsion_enb_us_blend_ewma.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\r041_us_blend_train\20260625_094715\risk_parity_lw_cov\baseline_us_blend_ewma_baseline_20260625_094716_843648`
- Baseline 配置：`D:\strategy\platform\configs\baseline_us_blend_ewma.yaml`

## 候选指标
- 累计收益率：154.97%
- 年化收益率：16.31%
- 年化波动率：19.20%
- 最大回撤：-26.53%
- 夏普比率：0.8497
- 成交金额合计：14443826.4640
- 金额换手率：458.18%
- 年化金额换手率：73.97%
- 成交数量合计：4657600.0000
- 年化数量换手：375949.7758
- 成交笔数：253
- 订单数：253
- 拒单数：0
- 跳过订单数：23
- 低于一手或现金不足跳过数：23
- 最大待执行意图数：6
- 平均现金权重：2.20%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：0.0875
- 年化收益率差值：0.0065
- 年化波动率差值：0.0049
- 最大回撤差值：-0.0037
- 夏普比率差值：0.0128
- 成交金额合计差值：1218699.7316
- 金额换手率差值：0.3109
- 年化金额换手率差值：0.0502
- 成交数量合计差值：695700.0000
- 年化数量换手差值：56155.1570
- 成交笔数差值：19.0000
- 订单数差值：19.0000
- 拒单数差值：0.0000
- 跳过订单数差值：2.0000
- 低于一手或现金不足跳过数差值：2.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：-0.0003

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
