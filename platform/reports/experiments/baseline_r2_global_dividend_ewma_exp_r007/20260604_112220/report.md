# 平台实验报告：baseline_r2_global_dividend_ewma_exp_r007

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_r2_global_dividend_ewma_exp_r007\20260604_112220\risk_parity_dcc_garch_momentum\baseline_r2_global_dividend_ewma_candidate_20260604_112220`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\generated\baseline_r2_global_dividend_ewma_candidate_r007.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_r2_global_dividend_ewma_exp_r007\20260604_112220\risk_parity_lw_cov\baseline_r2_global_dividend_ewma_baseline_20260604_112241`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\baseline_r2_global_dividend_ewma.yaml`

## 候选指标
- 累计收益率：22.39%
- 年化收益率：2.94%
- 年化波动率：4.45%
- 最大回撤：-5.57%
- 夏普比率：0.6603
- 年化换手：1253629.5493
- 成交笔数：37
- 订单数：37
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：71.89%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0718
- 年化收益率差值：-0.0084
- 年化波动率差值：0.0198
- 最大回撤差值：-0.0267
- 夏普比率差值：-0.8707
- 年化换手差值：783665.9569
- 成交笔数差值：0.0000
- 订单数差值：0.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0608

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
