# 平台实验报告：baseline_r1_domestic_rolling_exp_r004

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\results\backtests\baseline_r1_domestic_rolling_exp_r004\20260603_231018\risk_parity_garch_semivar\baseline_r1_domestic_rolling_candidate_20260603_231018`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\configs\generated\baseline_r1_domestic_rolling_candidate_r004.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\results\backtests\baseline_r1_domestic_rolling_exp_r004\20260603_231018\risk_parity\baseline_r1_domestic_rolling_baseline_20260603_231043`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\configs\baseline_r1_domestic_rolling.yaml`

## 候选指标
- 累计收益率：29.55%
- 年化收益率：3.78%
- 年化波动率：2.62%
- 最大回撤：-4.56%
- 夏普比率：1.4451
- 年化换手：328118.5932
- 成交笔数：30
- 订单数：30
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：65.25%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：0.0196
- 年化收益率差值：0.0023
- 年化波动率差值：0.0008
- 最大回撤差值：-0.0007
- 夏普比率差值：0.0412
- 年化换手差值：112223.4087
- 成交笔数差值：14.0000
- 订单数差值：14.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：-1.0000
- 平均现金权重差值：0.0019

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
