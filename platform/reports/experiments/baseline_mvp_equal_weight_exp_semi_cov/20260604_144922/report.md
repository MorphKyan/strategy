# 平台实验报告：baseline_mvp_equal_weight_exp_semi_cov

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_mvp_equal_weight_exp_semi_cov\20260604_144922\risk_parity_semi_cov\baseline_mvp_equal_weight_candidate_20260604_144922`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_mvp_equal_weight_candidate_semi_cov.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_mvp_equal_weight_exp_semi_cov\20260604_144922\monthly_equal_weight\baseline_mvp_equal_weight_baseline_20260604_144924`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\baseline_mvp_equal_weight.yaml`

## 候选指标
- 累计收益率：25.28%
- 年化收益率：9.31%
- 年化波动率：3.74%
- 最大回撤：-3.59%
- 夏普比率：2.4911
- 年化换手：852258.9867
- 成交笔数：26
- 订单数：26
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：6.38%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.3037
- 年化收益率差值：-0.0979
- 年化波动率差值：-0.0612
- 最大回撤差值：0.0755
- 夏普比率差值：0.5531
- 年化换手差值：105590.8187
- 成交笔数差值：-51.0000
- 订单数差值：-51.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0565

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
