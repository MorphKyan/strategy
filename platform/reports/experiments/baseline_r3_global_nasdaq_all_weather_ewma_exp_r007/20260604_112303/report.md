# 平台实验报告：baseline_r3_global_nasdaq_all_weather_ewma_exp_r007

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_r3_global_nasdaq_all_weather_ewma_exp_r007\20260604_112303\risk_parity_dcc_garch_momentum\baseline_r3_global_nasdaq_all_weather_ewma_candidate_20260604_112303`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\generated\baseline_r3_global_nasdaq_all_weather_ewma_candidate_r007.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_r3_global_nasdaq_all_weather_ewma_exp_r007\20260604_112303\risk_parity_lw_cov\baseline_r3_global_nasdaq_all_weather_ewma_baseline_20260604_112314`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\baseline_r3_global_nasdaq_all_weather_ewma.yaml`

## 候选指标
- 累计收益率：23.07%
- 年化收益率：5.55%
- 年化波动率：5.30%
- 最大回撤：-6.66%
- 夏普比率：1.0472
- 年化换手：2975803.1725
- 成交笔数：77
- 订单数：77
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：37.57%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0282
- 年化收益率差值：-0.0062
- 年化波动率差值：0.0178
- 最大回撤差值：-0.0299
- 夏普比率差值：-0.7057
- 年化换手差值：2105987.5755
- 成交笔数差值：13.0000
- 订单数差值：13.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：-1.0000
- 平均现金权重差值：-0.0054

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
