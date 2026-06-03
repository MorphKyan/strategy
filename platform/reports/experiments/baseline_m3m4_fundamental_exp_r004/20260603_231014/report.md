# 平台实验报告：baseline_m3m4_fundamental_exp_r004

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\results\backtests\baseline_m3m4_fundamental_exp_r004\20260603_231014\risk_parity_garch_semivar\baseline_m3m4_fundamental_candidate_20260603_231015`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\configs\generated\baseline_m3m4_fundamental_candidate_r004.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\results\backtests\baseline_m3m4_fundamental_exp_r004\20260603_231014\fundamental_value_equal_weight\baseline_m3m4_fundamental_baseline_20260603_231016`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\configs\baseline_m3m4_fundamental.yaml`

## 候选指标
- 累计收益率：33.50%
- 年化收益率：12.09%
- 年化波动率：3.23%
- 最大回撤：-2.04%
- 夏普比率：3.7429
- 年化换手：1478544.8742
- 成交笔数：50
- 订单数：50
- 拒单数：0
- 最大待执行意图数：3
- 平均现金权重：5.66%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：0.3350
- 年化收益率差值：0.1209
- 年化波动率差值：0.0323
- 最大回撤差值：-0.0204
- 夏普比率差值：3.7429
- 年化换手差值：1478544.8742
- 成交笔数差值：50.0000
- 订单数差值：50.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：3.0000
- 平均现金权重差值：-0.9434

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
