# 平台实验报告：baseline_r2_global_dividend_ewma_exp

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_r2_global_dividend_ewma_exp\20260603_154621\risk_parity_lw_cov\baseline_r2_global_dividend_ewma_candidate_20260603_154621`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_r2_global_dividend_ewma_candidate.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_r2_global_dividend_ewma_exp\20260603_154621\risk_parity_ewma\baseline_r2_global_dividend_ewma_baseline_20260603_154640`
- Baseline 配置：`D:\strategy\platform\configs\baseline_r2_global_dividend_ewma.yaml`

## 候选指标
- 累计收益率：66.93%
- 年化收益率：7.62%
- 年化波动率：3.63%
- 最大回撤：-4.17%
- 夏普比率：2.0998
- 年化换手：371963.5250
- 成交笔数：47
- 订单数：47
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：4.21%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0231
- 年化收益率差值：-0.0021
- 年化波动率差值：-0.0013
- 最大回撤差值：0.0026
- 夏普比率差值：0.0166
- 年化换手差值：-308286.9118
- 成交笔数差值：-33.0000
- 订单数差值：-33.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0026

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
