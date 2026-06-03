# 平台实验报告：platform_risk_parity_exp

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\eea35390-25f4-415c-ba00-621f8ce460d6\.system_generated\worktrees\subagent-Quant-Researcher-quant-researcher-8199568d\platform\results\backtests\platform_risk_parity_exp\20260603_150135\risk_parity_lw_cov\platform_risk_parity_candidate_20260603_150135`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\eea35390-25f4-415c-ba00-621f8ce460d6\.system_generated\worktrees\subagent-Quant-Researcher-quant-researcher-8199568d\platform\configs\generated\platform_risk_parity_candidate.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\eea35390-25f4-415c-ba00-621f8ce460d6\.system_generated\worktrees\subagent-Quant-Researcher-quant-researcher-8199568d\platform\results\backtests\platform_risk_parity_exp\20260603_150135\risk_parity\platform_risk_parity_baseline_20260603_150139`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\eea35390-25f4-415c-ba00-621f8ce460d6\.system_generated\worktrees\subagent-Quant-Researcher-quant-researcher-8199568d\platform\configs\platform_risk_parity.yaml`

## 候选指标
- 累计收益率：24.88%
- 年化收益率：2.68%
- 年化波动率：1.81%
- 最大回撤：-3.04%
- 夏普比率：1.4800
- 年化换手：181191.3943
- 成交笔数：15
- 订单数：15
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：71.22%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0084
- 年化收益率差值：-0.0008
- 年化波动率差值：-0.0009
- 最大回撤差值：0.0029
- 夏普比率差值：0.0260
- 年化换手差值：909.1683
- 成交笔数差值：0.0000
- 订单数差值：0.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0001

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
