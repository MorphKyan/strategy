# 平台实验报告：baseline_r2_global_dividend_ewma_exp_semi_cov

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_r2_global_dividend_ewma_exp_semi_cov\20260604_150057\risk_parity_semi_cov\baseline_r2_global_dividend_ewma_candidate_20260604_150057`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r2_global_dividend_ewma_candidate_semi_cov.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_r2_global_dividend_ewma_exp_semi_cov\20260604_150057\risk_parity_lw_cov\baseline_r2_global_dividend_ewma_baseline_20260604_150130`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\baseline_r2_global_dividend_ewma.yaml`

## 候选指标
- 累计收益率：25.11%
- 年化收益率：3.26%
- 年化波动率：2.39%
- 最大回撤：-4.03%
- 夏普比率：1.3654
- 年化换手：302742.7914
- 成交笔数：28
- 订单数：28
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：66.16%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0445
- 年化收益率差值：-0.0052
- 年化波动率差值：-0.0008
- 最大回撤差值：-0.0113
- 夏普比率差值：-0.1656
- 年化换手差值：-167220.8010
- 成交笔数差值：-9.0000
- 订单数差值：-9.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0035

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
