# 平台实验报告：r037_r1_halflife_vs_r016_train

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`D:\strategy\platform\results\backtests\r037_r1_halflife_vs_r016_train\20260624_235300\half_life_adaptive_risk_parity\research_r037_r1_halflife_train_candidate_20260624_235300_491705`
- 候选配置：`D:\strategy\platform\configs\research_r037_r1_halflife_train.yaml`
- Baseline 原始结果路径：`D:\strategy\platform\results\backtests\r037_r1_halflife_vs_r016_train\20260624_235300\adaptive_risk_deviation_volatility_triggered\research_r037_r1_r016_train_baseline_20260624_235315_993879`
- Baseline 配置：`D:\strategy\platform\configs\research_r037_r1_r016_train.yaml`

## 候选指标
- 累计收益率：123.27%
- 年化收益率：14.08%
- 年化波动率：11.21%
- 最大回撤：-15.28%
- 夏普比率：1.2557
- 成交金额合计：5733303.4025
- 金额换手率：196.97%
- 年化金额换手率：32.29%
- 成交数量合计：1525300.0000
- 年化数量换手：125040.8588
- 成交笔数：179
- 订单数：179
- 拒单数：0
- 跳过订单数：23
- 低于一手或现金不足跳过数：23
- 最大待执行意图数：4
- 平均现金权重：2.36%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：0.0229
- 年化收益率差值：0.0019
- 年化波动率差值：0.0047
- 最大回撤差值：-0.0106
- 夏普比率差值：-0.0370
- 成交金额合计差值：-373529.5900
- 金额换手率差值：-0.1448
- 年化金额换手率差值：-0.0237
- 成交数量合计差值：-60900.0000
- 年化数量换手差值：-4992.4528
- 成交笔数差值：64.0000
- 订单数差值：63.0000
- 拒单数差值：-1.0000
- 跳过订单数差值：3.0000
- 低于一手或现金不足跳过数差值：3.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0008

## 建议
- `继续改进` 为标准实验报告自动默认建议，已由 R037 主报告覆盖。本候选在训练样本和起点敏感性中未通过验收，R037 结论为 `Failed`，拒绝合入，不应保留策略注册或平台配置。

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
