# 平台实验报告： risk_parity_ewma

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径： `D:\strategy\platform\results\backtests\risk_parity_ewma\20260530_223647\risk_parity_ewma\platform_risk_parity_ewma_candidate_20260530_223647`
- 候选配置： `D:\strategy\platform\configs\platform_risk_parity_ewma.yaml`
- Baseline 原始结果路径： `D:\strategy\platform\results\backtests\risk_parity_ewma\20260530_223647\risk_parity\platform_risk_parity_baseline_20260530_223700`
- Baseline 配置： `D:\strategy\platform\configs\platform_risk_parity.yaml`

## 候选指标
- 累计收益率： 63.10%
- 年化收益率： 6.00%
- 年化波动率： 3.53%
- 最大回撤： -3.94%
- 夏普比率： 1.7026
- 年化换手： 679472.8605
- 成交笔数： 87
- 订单数： 1117
- 拒单数： 1030
- 最大待执行意图数： 2
- 平均现金权重： 1.81%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 1030

## Baseline 对比
- 累计收益率差值： 0.0227
- 年化收益率差值： 0.0018
- 年化波动率差值： -0.0000
- 最大回撤差值： 0.0043
- 夏普比率差值： 0.0519
- 年化换手差值： 224900.4102
- 成交笔数差值： 30.0000
- 订单数差值： -79.0000
- rejected_订单数差值： -109.0000
- 最大待执行意图数差值： 0.0000
- 平均现金权重差值： -0.0005

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
