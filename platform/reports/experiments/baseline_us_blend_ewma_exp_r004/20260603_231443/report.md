# 平台实验报告：baseline_us_blend_ewma_exp_r004

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\results\backtests\baseline_us_blend_ewma_exp_r004\20260603_231443\risk_parity_garch_semivar\baseline_us_blend_ewma_candidate_20260603_231444`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\configs\generated\baseline_us_blend_ewma_candidate_r004.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\results\backtests\baseline_us_blend_ewma_exp_r004\20260603_231443\risk_parity_ewma\baseline_us_blend_ewma_baseline_20260603_231519`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\configs\baseline_us_blend_ewma.yaml`

## 候选指标
- 累计收益率：32.97%
- 年化收益率：4.17%
- 年化波动率：2.82%
- 最大回撤：-4.02%
- 夏普比率：1.4802
- 年化换手：540032.7574
- 成交笔数：63
- 订单数：63
- 拒单数：0
- 最大待执行意图数：3
- 平均现金权重：65.87%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0288
- 年化收益率差值：-0.0032
- 年化波动率差值：-0.0035
- 最大回撤差值：0.0066
- 夏普比率差值：0.0633
- 年化换手差值：113642.2533
- 成交笔数差值：3.0000
- 订单数差值：3.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0002

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
