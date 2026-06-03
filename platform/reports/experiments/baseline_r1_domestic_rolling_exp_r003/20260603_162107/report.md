# 平台实验报告：baseline_r1_domestic_rolling_exp_r003

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_r1_domestic_rolling_exp_r003\20260603_162107\risk_parity_dynamic_budget\baseline_r1_domestic_rolling_candidate_20260603_162107`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_r1_domestic_rolling_candidate_r003.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_r1_domestic_rolling_exp_r003\20260603_162107\risk_parity\baseline_r1_domestic_rolling_baseline_20260603_162128`
- Baseline 配置：`D:\strategy\platform\configs\baseline_r1_domestic_rolling.yaml`

## 候选指标
- 累计收益率：22.48%
- 年化收益率：2.95%
- 年化波动率：2.55%
- 最大回撤：-3.75%
- 夏普比率：1.1564
- 年化换手：229061.1324
- 成交笔数：17
- 订单数：17
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：71.04%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0510
- 年化收益率差值：-0.0060
- 年化波动率差值：0.0002
- 最大回撤差值：0.0074
- 夏普比率差值：-0.2475
- 年化换手差值：13165.9480
- 成交笔数差值：1.0000
- 订单数差值：1.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：-1.0000
- 平均现金权重差值：0.0598

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
