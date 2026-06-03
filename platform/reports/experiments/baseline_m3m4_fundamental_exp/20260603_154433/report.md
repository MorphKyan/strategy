# 平台实验报告：baseline_m3m4_fundamental_exp

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_m3m4_fundamental_exp\20260603_154433\risk_parity_lw_cov\baseline_m3m4_fundamental_candidate_20260603_154433`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_m3m4_fundamental_candidate.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_m3m4_fundamental_exp\20260603_154433\fundamental_value_equal_weight\baseline_m3m4_fundamental_baseline_20260603_154437`
- Baseline 配置：`D:\strategy\platform\configs\baseline_m3m4_fundamental.yaml`

## 候选指标
- 累计收益率：26.77%
- 年化收益率：2.85%
- 年化波动率：1.74%
- 最大回撤：-2.27%
- 夏普比率：1.6426
- 年化换手：220797.1186
- 成交笔数：30
- 订单数：30
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：71.12%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：0.2677
- 年化收益率差值：0.0285
- 年化波动率差值：0.0174
- 最大回撤差值：-0.0227
- 夏普比率差值：1.6426
- 年化换手差值：220797.1186
- 成交笔数差值：30.0000
- 订单数差值：30.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：2.0000
- 平均现金权重差值：-0.2888

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
