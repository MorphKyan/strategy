# 平台实验报告：baseline_us_blend_ewma_exp

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_us_blend_ewma_exp\20260603_154723\risk_parity_lw_cov\baseline_us_blend_ewma_candidate_20260603_154723`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_us_blend_ewma_candidate.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_us_blend_ewma_exp\20260603_154723\risk_parity_ewma\baseline_us_blend_ewma_baseline_20260603_154745`
- Baseline 配置：`D:\strategy\platform\configs\baseline_us_blend_ewma.yaml`

## 候选指标
- 累计收益率：29.55%
- 年化收益率：3.78%
- 年化波动率：2.52%
- 最大回撤：-3.43%
- 夏普比率：1.4998
- 年化换手：274278.9919
- 成交笔数：36
- 订单数：36
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：65.55%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0389
- 年化收益率差值：-0.0044
- 年化波动率差值：-0.0065
- 最大回撤差值：0.0191
- 夏普比率差值：0.1693
- 年化换手差值：-114270.8857
- 成交笔数差值：-15.0000
- 订单数差值：-15.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：-1.0000
- 平均现金权重差值：0.0038

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
