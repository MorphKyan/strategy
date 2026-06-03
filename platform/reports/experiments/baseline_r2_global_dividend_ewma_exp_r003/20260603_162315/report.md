# 平台实验报告：baseline_r2_global_dividend_ewma_exp_r003

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_r2_global_dividend_ewma_exp_r003\20260603_162315\risk_parity_dynamic_budget\baseline_r2_global_dividend_ewma_candidate_20260603_162315`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_r2_global_dividend_ewma_candidate_r003.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_r2_global_dividend_ewma_exp_r003\20260603_162315\risk_parity_ewma\baseline_r2_global_dividend_ewma_baseline_20260603_162338`
- Baseline 配置：`D:\strategy\platform\configs\baseline_r2_global_dividend_ewma.yaml`

## 候选指标
- 累计收益率：20.85%
- 年化收益率：2.75%
- 年化波动率：2.54%
- 最大回撤：-4.23%
- 夏普比率：1.0821
- 年化换手：222558.9188
- 成交笔数：24
- 订单数：24
- 拒单数：0
- 最大待执行意图数：3
- 平均现金权重：71.13%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0869
- 年化收益率差值：-0.0103
- 年化波动率差值：-0.0005
- 最大回撤差值：-0.0039
- 夏普比率差值：-0.3768
- 年化换手差值：-197199.6638
- 成交笔数差值：-13.0000
- 订单数差值：-13.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：1.0000
- 平均现金权重差值：0.0579

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
