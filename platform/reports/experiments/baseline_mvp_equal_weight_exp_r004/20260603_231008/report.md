# 平台实验报告：baseline_mvp_equal_weight_exp_r004

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\results\backtests\baseline_mvp_equal_weight_exp_r004\20260603_231008\risk_parity_garch_semivar\baseline_mvp_equal_weight_candidate_20260603_231008`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\configs\generated\baseline_mvp_equal_weight_candidate_r004.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\results\backtests\baseline_mvp_equal_weight_exp_r004\20260603_231008\monthly_equal_weight\baseline_mvp_equal_weight_baseline_20260603_231013`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\d7b43de1-bf98-4325-ab26-ff1006c4e272\.system_generated\worktrees\subagent-Quant-Researcher-1-quant-researcher-97090326\platform\configs\baseline_mvp_equal_weight.yaml`

## 候选指标
- 累计收益率：30.37%
- 年化收益率：11.04%
- 年化波动率：3.69%
- 最大回撤：-3.79%
- 夏普比率：2.9933
- 年化换手：894893.2111
- 成交笔数：24
- 订单数：24
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：6.36%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.2528
- 年化收益率差值：-0.0805
- 年化波动率差值：-0.0616
- 最大回撤差值：0.0734
- 夏普比率差值：1.0553
- 年化换手差值：148225.0432
- 成交笔数差值：-53.0000
- 订单数差值：-53.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0563

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
