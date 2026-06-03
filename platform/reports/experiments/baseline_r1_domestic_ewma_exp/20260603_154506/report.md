# 平台实验报告：baseline_r1_domestic_ewma_exp

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_r1_domestic_ewma_exp\20260603_154506\risk_parity_lw_cov\baseline_r1_domestic_ewma_candidate_20260603_154506`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_r1_domestic_ewma_candidate.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_r1_domestic_ewma_exp\20260603_154506\risk_parity_ewma\baseline_r1_domestic_ewma_baseline_20260603_154520`
- Baseline 配置：`D:\strategy\platform\configs\baseline_r1_domestic_ewma.yaml`

## 候选指标
- 累计收益率：24.87%
- 年化收益率：3.23%
- 年化波动率：2.30%
- 最大回撤：-3.88%
- 夏普比率：1.4044
- 年化换手：209097.9270
- 成交笔数：16
- 订单数：16
- 拒单数：0
- 最大待执行意图数：3
- 平均现金权重：64.88%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0242
- 年化收益率差值：-0.0028
- 年化波动率差值：-0.0016
- 最大回撤差值：-0.0030
- 夏普比率差值：-0.0233
- 年化换手差值：-128292.4232
- 成交笔数差值：-15.0000
- 订单数差值：-15.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：1.0000
- 平均现金权重差值：-0.0033

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
