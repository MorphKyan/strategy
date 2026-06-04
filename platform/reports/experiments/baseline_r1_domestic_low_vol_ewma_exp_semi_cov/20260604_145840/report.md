# 平台实验报告：baseline_r1_domestic_low_vol_ewma_exp_semi_cov

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_r1_domestic_low_vol_ewma_exp_semi_cov\20260604_145840\risk_parity_semi_cov\baseline_r1_domestic_low_vol_ewma_candidate_20260604_145840`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r1_domestic_low_vol_ewma_candidate_semi_cov.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_r1_domestic_low_vol_ewma_exp_semi_cov\20260604_145840\risk_parity_ewma\baseline_r1_domestic_low_vol_ewma_baseline_20260604_145913`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\baseline_r1_domestic_low_vol_ewma.yaml`

## 候选指标
- 累计收益率：23.89%
- 年化收益率：3.12%
- 年化波动率：2.25%
- 最大回撤：-3.54%
- 夏普比率：1.3854
- 年化换手：238556.7980
- 成交笔数：21
- 订单数：21
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：65.74%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0264
- 年化收益率差值：-0.0031
- 年化波动率差值：-0.0014
- 最大回撤差值：-0.0049
- 夏普比率差值：-0.0502
- 年化换手差值：-147251.7176
- 成交笔数差值：-5.0000
- 订单数差值：-5.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0017

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
