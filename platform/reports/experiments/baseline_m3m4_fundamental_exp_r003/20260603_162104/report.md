# 平台实验报告：baseline_m3m4_fundamental_exp_r003

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_m3m4_fundamental_exp_r003\20260603_162104\risk_parity_dynamic_budget\baseline_m3m4_fundamental_candidate_20260603_162105`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_m3m4_fundamental_candidate_r003.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_m3m4_fundamental_exp_r003\20260603_162104\fundamental_value_equal_weight\baseline_m3m4_fundamental_baseline_20260603_162106`
- Baseline 配置：`D:\strategy\platform\configs\baseline_m3m4_fundamental.yaml`

## 候选指标
- 累计收益率：26.10%
- 年化收益率：9.59%
- 年化波动率：3.86%
- 最大回撤：-3.36%
- 夏普比率：2.4856
- 年化换手：761039.2753
- 成交笔数：30
- 订单数：30
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：19.63%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：0.2610
- 年化收益率差值：0.0959
- 年化波动率差值：0.0386
- 最大回撤差值：-0.0336
- 夏普比率差值：2.4856
- 年化换手差值：761039.2753
- 成交笔数差值：30.0000
- 订单数差值：30.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：2.0000
- 平均现金权重差值：-0.8037

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
