# 平台实验报告：baseline_risk_parity_lw_cov_exp_semi_cov

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_risk_parity_lw_cov_exp_semi_cov\20260604_150346\risk_parity_semi_cov\platform_risk_parity_lw_cov_candidate_20260604_150346`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_risk_parity_lw_cov_candidate_semi_cov.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_risk_parity_lw_cov_exp_semi_cov\20260604_150346\risk_parity_lw_cov\platform_risk_parity_lw_cov_baseline_20260604_150347`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\baseline_risk_parity_lw_cov.yaml`

## 候选指标
- 累计收益率：24.99%
- 年化收益率：9.35%
- 年化波动率：3.76%
- 最大回撤：-3.59%
- 夏普比率：2.4865
- 年化换手：864434.1151
- 成交笔数：26
- 订单数：26
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：6.46%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0186
- 年化收益率差值：-0.0065
- 年化波动率差值：0.0001
- 最大回撤差值：0.0091
- 夏普比率差值：-0.1806
- 年化换手差值：284862.9405
- 成交笔数差值：16.0000
- 订单数差值：16.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：1.0000
- 平均现金权重差值：0.0120

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
