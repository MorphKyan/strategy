# 平台实验报告：baseline_r2_global_ewma_exp_r004

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\results\backtests\baseline_r2_global_ewma_exp_r004\20260603_231158\risk_parity_garch_semivar\baseline_r2_global_ewma_candidate_20260603_231158`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\configs\generated\baseline_r2_global_ewma_candidate_r004.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\results\backtests\baseline_r2_global_ewma_exp_r004\20260603_231158\risk_parity_ewma\baseline_r2_global_ewma_baseline_20260603_231223`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\configs\baseline_r2_global_ewma.yaml`

## 候选指标
- 累计收益率：31.07%
- 年化收益率：3.95%
- 年化波动率：2.57%
- 最大回撤：-3.81%
- 夏普比率：1.5373
- 年化换手：543024.1804
- 成交笔数：54
- 订单数：54
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：65.85%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0127
- 年化收益率差值：-0.0014
- 年化波动率差值：-0.0022
- 最大回撤差值：0.0037
- 夏普比率差值：0.0698
- 年化换手差值：102938.5302
- 成交笔数差值：7.0000
- 订单数差值：7.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：-1.0000
- 平均现金权重差值：0.0067

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
