# 平台实验报告：baseline_us_blend_ewma_exp_semi_cov

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_us_blend_ewma_exp_semi_cov\20260604_150238\risk_parity_semi_cov\baseline_us_blend_ewma_candidate_20260604_150238`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_us_blend_ewma_candidate_semi_cov.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_us_blend_ewma_exp_semi_cov\20260604_150238\risk_parity_lw_cov\baseline_us_blend_ewma_baseline_20260604_150311`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\baseline_us_blend_ewma.yaml`

## 候选指标
- 累计收益率：28.99%
- 年化收益率：3.72%
- 年化波动率：2.74%
- 最大回撤：-4.10%
- 夏普比率：1.3553
- 年化换手：372196.0380
- 成交笔数：63
- 订单数：63
- 拒单数：0
- 最大待执行意图数：3
- 平均现金权重：66.31%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0276
- 年化收益率差值：-0.0031
- 年化波动率差值：0.0003
- 最大回撤差值：-0.0081
- 夏普比率差值：-0.1303
- 年化换手差值：-194062.2269
- 成交笔数差值：6.0000
- 订单数差值：6.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0099

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
