# 平台实验报告：r041_smoke_r2_train

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\r041_smoke_r2_train\20260625_094646\risk_parity_min_torsion_enb\r041_min_torsion_enb_r2_global_ewma_candidate_20260625_094646_866936`
- 候选配置：`D:\strategy\platform\configs\r041_min_torsion_enb_r2_global_ewma.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\r041_smoke_r2_train\20260625_094646\risk_parity_lw_cov\baseline_r2_global_ewma_baseline_20260625_094654_603628`
- Baseline 配置：`D:\strategy\platform\configs\baseline_r2_global_ewma.yaml`

## 候选指标
- 累计收益率：136.57%
- 年化收益率：14.91%
- 年化波动率：11.07%
- 最大回撤：-11.48%
- 夏普比率：1.3472
- 成交金额合计：16425544.1134
- 金额换手率：537.70%
- 年化金额换手率：86.80%
- 成交数量合计：5057500.0000
- 年化数量换手：408228.6996
- 成交笔数：379
- 订单数：380
- 拒单数：1
- 跳过订单数：40
- 低于一手或现金不足跳过数：40
- 最大待执行意图数：5
- 平均现金权重：2.30%
- 是否有样本外指标：否

## 候选执行拒单
- `limit_down`: 1

## Baseline 对比
- 累计收益率差值：0.0523
- 年化收益率差值：0.0041
- 年化波动率差值：-0.0012
- 最大回撤差值：-0.0007
- 夏普比率差值：0.0510
- 成交金额合计差值：2054412.8946
- 金额换手率差值：0.6195
- 年化金额换手率差值：0.1000
- 成交数量合计差值：561500.0000
- 年化数量换手差值：45322.8700
- 成交笔数差值：44.0000
- 订单数差值：44.0000
- 拒单数差值：0.0000
- 跳过订单数差值：8.0000
- 低于一手或现金不足跳过数差值：8.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：-0.0001

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
