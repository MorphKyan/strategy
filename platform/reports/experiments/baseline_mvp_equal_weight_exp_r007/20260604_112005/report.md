# 平台实验报告：baseline_mvp_equal_weight_exp_r007

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_mvp_equal_weight_exp_r007\20260604_112005\risk_parity_dcc_garch_momentum\baseline_mvp_equal_weight_candidate_20260604_112005`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\generated\baseline_mvp_equal_weight_candidate_r007.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_mvp_equal_weight_exp_r007\20260604_112005\monthly_equal_weight\baseline_mvp_equal_weight_baseline_20260604_112006`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\baseline_mvp_equal_weight.yaml`

## 候选指标
- 累计收益率：27.27%
- 年化收益率：9.99%
- 年化波动率：7.10%
- 最大回撤：-6.17%
- 夏普比率：1.4084
- 年化换手：3401867.5232
- 成交笔数：26
- 订单数：26
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：7.94%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.2838
- 年化收益率差值：-0.0910
- 年化波动率差值：-0.0276
- 最大回撤差值：0.0497
- 夏普比率差值：-0.5296
- 年化换手差值：2655199.3553
- 成交笔数差值：-51.0000
- 订单数差值：-51.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0721

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
