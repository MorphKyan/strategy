# 平台实验报告：risk_parity_ewma

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\risk_parity_ewma\20260531_111539\risk_parity_ewma\platform_risk_parity_ewma_candidate_20260531_111539`
- 候选配置：`D:\strategy\platform\configs\platform_risk_parity_ewma.yaml`

## 候选指标
- 累计收益率：59.96%
- 年化收益率：5.76%
- 年化波动率：3.46%
- 最大回撤：-3.92%
- 夏普比率：1.6620
- 年化换手：619128.9557
- 成交笔数：72
- 订单数：72
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：2.90%
- 是否有样本外指标：否

## Baseline 对比
- 本次未请求 baseline 对比。

## 建议
- 复核

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
