# 平台实验报告：baseline_r1_domestic_rolling_exp_r007

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_r1_domestic_rolling_exp_r007\20260604_112010\risk_parity_dcc_garch_momentum\baseline_r1_domestic_rolling_candidate_20260604_112010`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\generated\baseline_r1_domestic_rolling_candidate_r007.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_r1_domestic_rolling_exp_r007\20260604_112010\risk_parity\baseline_r1_domestic_rolling_baseline_20260604_112032`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\baseline_r1_domestic_rolling.yaml`

## 候选指标
- 累计收益率：19.10%
- 年化收益率：2.54%
- 年化波动率：4.41%
- 最大回撤：-6.44%
- 夏普比率：0.5753
- 年化换手：1381940.1880
- 成交笔数：38
- 订单数：38
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：65.68%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0848
- 年化收益率差值：-0.0102
- 年化波动率差值：0.0188
- 最大回撤差值：-0.0195
- 夏普比率差值：-0.8287
- 年化换手差值：1166045.0035
- 成交笔数差值：22.0000
- 订单数差值：22.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：-1.0000
- 平均现金权重差值：0.0062

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
