# 平台实验报告：baseline_mvp_equal_weight_exp_r003

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\baseline_mvp_equal_weight_exp_r003\20260603_162102\risk_parity_dynamic_budget\baseline_mvp_equal_weight_candidate_20260603_162102`
- 候选配置：`D:\strategy\platform\configs\generated\baseline_mvp_equal_weight_candidate_r003.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\baseline_mvp_equal_weight_exp_r003\20260603_162102\monthly_equal_weight\baseline_mvp_equal_weight_baseline_20260603_162103`
- Baseline 配置：`D:\strategy\platform\configs\baseline_mvp_equal_weight.yaml`

## 候选指标
- 累计收益率：23.43%
- 年化收益率：8.67%
- 年化波动率：3.99%
- 最大回撤：-4.53%
- 夏普比率：2.1740
- 年化换手：612686.9855
- 成交笔数：15
- 订单数：15
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：19.55%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.3222
- 年化收益率差值：-0.1043
- 年化波动率差值：-0.0587
- 最大回撤差值：0.0661
- 夏普比率差值：0.2360
- 年化换手差值：-133981.1825
- 成交笔数差值：-62.0000
- 订单数差值：-62.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.1882

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
