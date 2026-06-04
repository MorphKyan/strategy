# 平台实验报告：baseline_r1_domestic_ewma_exp_semi_cov

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_r1_domestic_ewma_exp_semi_cov\20260604_145729\risk_parity_semi_cov\baseline_r1_domestic_ewma_candidate_20260604_145729`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r1_domestic_ewma_candidate_semi_cov.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_r1_domestic_ewma_exp_semi_cov\20260604_145729\risk_parity_ewma\baseline_r1_domestic_ewma_baseline_20260604_145803`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\baseline_r1_domestic_ewma.yaml`

## 候选指标
- 累计收益率：24.68%
- 年化收益率：3.21%
- 年化波动率：2.48%
- 最大回撤：-3.73%
- 夏普比率：1.2938
- 年化换手：311775.7516
- 成交笔数：33
- 订单数：33
- 拒单数：0
- 最大待执行意图数：3
- 平均现金权重：65.98%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0452
- 年化收益率差值：-0.0053
- 年化波动率差值：-0.0005
- 最大回撤差值：-0.0036
- 夏普比率差值：-0.1812
- 年化换手差值：-103650.3113
- 成交笔数差值：-4.0000
- 订单数差值：-4.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0051

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
