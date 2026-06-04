# 平台实验报告：baseline_r2_global_ewma_exp_r007

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_r2_global_ewma_exp_r007\20260604_112137\risk_parity_dcc_garch_momentum\baseline_r2_global_ewma_candidate_20260604_112137`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\generated\baseline_r2_global_ewma_candidate_r007.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_r2_global_ewma_exp_r007\20260604_112137\risk_parity_lw_cov\baseline_r2_global_ewma_baseline_20260604_112158`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\baseline_r2_global_ewma.yaml`

## 候选指标
- 累计收益率：19.52%
- 年化收益率：2.59%
- 年化波动率：4.36%
- 最大回撤：-6.44%
- 夏普比率：0.5932
- 年化换手：1548893.3926
- 成交笔数：52
- 订单数：52
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：66.10%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.1171
- 年化收益率差值：-0.0138
- 年化波动率差值：0.0180
- 最大回撤差值：-0.0335
- 夏普比率差值：-0.9591
- 年化换手差值：1069853.3354
- 成交笔数差值：-1.0000
- 订单数差值：-1.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：-1.0000
- 平均现金权重差值：0.0082

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
