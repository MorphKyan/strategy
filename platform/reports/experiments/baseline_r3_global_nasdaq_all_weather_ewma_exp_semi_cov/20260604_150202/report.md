# 平台实验报告：baseline_r3_global_nasdaq_all_weather_ewma_exp_semi_cov

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_r3_global_nasdaq_all_weather_ewma_exp_semi_cov\20260604_150202\risk_parity_semi_cov\baseline_r3_global_nasdaq_all_weather_ewma_candidate_20260604_150202`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r3_global_nasdaq_all_weather_ewma_candidate_semi_cov.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\results\backtests\baseline_r3_global_nasdaq_all_weather_ewma_exp_semi_cov\20260604_150202\risk_parity_lw_cov\baseline_r3_global_nasdaq_all_weather_ewma_baseline_20260604_150220`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\baseline_r3_global_nasdaq_all_weather_ewma.yaml`

## 候选指标
- 累计收益率：23.50%
- 年化收益率：5.64%
- 年化波动率：3.16%
- 最大回撤：-2.22%
- 夏普比率：1.7831
- 年化换手：645133.4633
- 成交笔数：61
- 订单数：61
- 拒单数：0
- 最大待执行意图数：3
- 平均现金权重：37.60%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0239
- 年化收益率差值：-0.0053
- 年化波动率差值：-0.0036
- 最大回撤差值：0.0144
- 夏普比率差值：0.0302
- 年化换手差值：-224682.1337
- 成交笔数差值：-3.0000
- 订单数差值：-3.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：-0.0051

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
