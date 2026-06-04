# 平台实验报告：baseline_m3m4_fundamental_exp_r007

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_m3m4_fundamental_exp_r007\20260604_112007\risk_parity_dcc_garch_momentum\baseline_m3m4_fundamental_candidate_20260604_112008`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\generated\baseline_m3m4_fundamental_candidate_r007.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_m3m4_fundamental_exp_r007\20260604_112007\fundamental_value_equal_weight\baseline_m3m4_fundamental_baseline_20260604_112009`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\baseline_m3m4_fundamental.yaml`

## 候选指标
- 累计收益率：39.67%
- 年化收益率：14.11%
- 年化波动率：6.79%
- 最大回撤：-5.00%
- 夏普比率：2.0778
- 年化换手：6585372.7459
- 成交笔数：83
- 订单数：83
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：7.64%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：0.3967
- 年化收益率差值：0.1411
- 年化波动率差值：0.0679
- 最大回撤差值：-0.0500
- 夏普比率差值：2.0778
- 年化换手差值：6585372.7459
- 成交笔数差值：83.0000
- 订单数差值：83.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：2.0000
- 平均现金权重差值：-0.9236

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
