# 平台实验报告：baseline_r1_domestic_low_vol_ewma_exp_r007

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_r1_domestic_low_vol_ewma_exp_r007\20260604_112411\risk_parity_dcc_garch_momentum\baseline_r1_domestic_low_vol_ewma_candidate_20260604_112411`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\generated\baseline_r1_domestic_low_vol_ewma_candidate_r007.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\results\backtests\baseline_r1_domestic_low_vol_ewma_exp_r007\20260604_112411\risk_parity_ewma\baseline_r1_domestic_low_vol_ewma_baseline_20260604_112431`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\6d9cb386-c516-4c86-855d-dcb410e441f7\.system_generated\worktrees\subagent-Quant-Researcher---R007-quant-researcher-0dc4724b\platform\configs\baseline_r1_domestic_low_vol_ewma.yaml`

## 候选指标
- 累计收益率：21.40%
- 年化收益率：2.82%
- 年化波动率：4.54%
- 最大回撤：-5.57%
- 夏普比率：0.6210
- 年化换手：1100424.6829
- 成交笔数：26
- 订单数：26
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：71.45%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0513
- 年化收益率差值：-0.0061
- 年化波动率差值：0.0215
- 最大回撤差值：-0.0251
- 夏普比率差值：-0.8147
- 年化换手差值：714616.1673
- 成交笔数差值：0.0000
- 订单数差值：0.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0587

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
