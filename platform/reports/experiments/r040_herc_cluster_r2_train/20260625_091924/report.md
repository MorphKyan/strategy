# 平台实验报告：r040_herc_cluster_r2_train

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\r040_herc_cluster_r2_train\20260625_091924\herc_cluster_risk_parity\r040_herc_cluster_r2_global_ewma_candidate_20260625_091924_878491`
- 候选配置：`D:\strategy\platform\configs\r040_herc_cluster_r2_global_ewma.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\r040_herc_cluster_r2_train\20260625_091924\risk_parity_lw_cov\baseline_r2_global_ewma_baseline_20260625_091931_742995`
- Baseline 配置：`D:\strategy\platform\configs\baseline_r2_global_ewma.yaml`

## 候选指标
- 累计收益率：91.67%
- 年化收益率：13.25%
- 年化波动率：11.03%
- 最大回撤：-13.00%
- 夏普比率：1.2006
- 成交金额合计：10304637.3462
- 金额换手率：393.35%
- 年化金额换手率：75.21%
- 成交数量合计：3001000.0000
- 年化数量换手：286893.7785
- 成交笔数：282
- 订单数：283
- 拒单数：1
- 跳过订单数：26
- 低于一手或现金不足跳过数：26
- 最大待执行意图数：5
- 平均现金权重：2.80%
- 是否有样本外指标：否

## 候选执行拒单
- `limit_down`: 1

## Baseline 对比
- 累计收益率差值：-0.0026
- 年化收益率差值：-0.0003
- 年化波动率差值：-0.0015
- 最大回撤差值：-0.0235
- 夏普比率差值：0.0130
- 成交金额合计差值：-978997.0931
- 金额换手率差值：-0.3344
- 年化金额换手率差值：-0.0639
- 成交数量合计差值：-373400.0000
- 年化数量换手差值：-35696.8134
- 成交笔数差值：-20.0000
- 订单数差值：-20.0000
- 拒单数差值：0.0000
- 跳过订单数差值：-8.0000
- 低于一手或现金不足跳过数差值：-8.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0005

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
