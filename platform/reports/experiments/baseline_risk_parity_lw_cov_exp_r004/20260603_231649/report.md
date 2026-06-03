# 平台实验报告：baseline_risk_parity_lw_cov_exp_r004

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\results\backtests\baseline_risk_parity_lw_cov_exp_r004\20260603_231649\risk_parity_garch_semivar\platform_risk_parity_lw_cov_candidate_20260603_231649`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\configs\generated\baseline_risk_parity_lw_cov_candidate_r004.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\results\backtests\baseline_risk_parity_lw_cov_exp_r004\20260603_231649\risk_parity_lw_cov\platform_risk_parity_lw_cov_baseline_20260603_231651`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\configs\baseline_risk_parity_lw_cov.yaml`

## 候选指标
- 累计收益率：30.06%
- 年化收益率：11.10%
- 年化波动率：3.71%
- 最大回撤：-3.79%
- 夏普比率：2.9914
- 年化换手：907677.3998
- 成交笔数：24
- 订单数：24
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：6.45%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：0.0321
- 年化收益率差值：0.0111
- 年化波动率差值：-0.0004
- 最大回撤差值：0.0071
- 夏普比率差值：0.3243
- 年化换手差值：328106.2252
- 成交笔数差值：14.0000
- 订单数差值：14.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：1.0000
- 平均现金权重差值：0.0120

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
