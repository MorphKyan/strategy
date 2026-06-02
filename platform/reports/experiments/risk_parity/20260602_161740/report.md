# 平台实验报告：risk_parity

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\risk_parity\20260602_161740\risk_parity\platform_risk_parity_candidate_20260602_161740`
- 候选配置：`D:\strategy\platform\configs\platform_risk_parity.yaml`

## 候选指标
- 累计收益率：61.19%
- 年化收益率：5.85%
- 年化波动率：3.51%
- 最大回撤：-4.37%
- 夏普比率：1.6685
- 年化换手：449285.9194
- 成交笔数：58
- 订单数：58
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：2.41%
- 是否有样本外指标：否

## Baseline 对比
- 本次未请求 baseline 对比。

## 建议
- 复核

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
