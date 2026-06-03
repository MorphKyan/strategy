# 平台实验报告：baseline_r2_global_ewma_exp

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_r2_global_ewma_exp\20260603_154537\risk_parity_lw_cov\baseline_r2_global_ewma_candidate_20260603_154537`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_r2_global_ewma_candidate.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_r2_global_ewma_exp\20260603_154537\risk_parity_ewma\baseline_r2_global_ewma_baseline_20260603_154558`
- Baseline 配置：`D:\strategy\platform\configs\baseline_r2_global_ewma.yaml`

## 候选指标
- 累计收益率：28.31%
- 年化收益率：3.64%
- 年化波动率：2.26%
- 最大回撤：-3.45%
- 夏普比率：1.6091
- 年化换手：222631.9512
- 成交笔数：21
- 订单数：21
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：65.08%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0097
- 年化收益率差值：-0.0011
- 年化波动率差值：-0.0042
- 最大回撤差值：0.0124
- 夏普比率差值：0.2108
- 年化换手差值：-140753.3862
- 成交笔数差值：-19.0000
- 订单数差值：-19.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：-0.0023

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
