# 平台实验报告：risk_parity_ewma_dd_recovery

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\risk_parity_ewma_dd_recovery\20260602_161703\risk_parity_ewma_dd_recovery\overseas_us_blend_ewma_dd_rec_candidate_20260602_161703`
- 候选配置：`D:\strategy\platform\configs\generated\platform_overseas_us_blend_ewma_dd_rec.yaml`

## 候选指标
- 累计收益率：76.73%
- 年化收益率：8.50%
- 年化波动率：4.85%
- 最大回撤：-7.20%
- 夏普比率：1.7542
- 年化换手：716356.3089
- 成交笔数：124
- 订单数：124
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：3.85%
- 是否有样本外指标：否

## Baseline 对比
- 本次未请求 baseline 对比。

## 建议
- 复核

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
