# 平台实验报告：risk_parity_lw_cov

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R001--quant-researcher-5cc36bdb\platform\results\backtests\risk_parity_lw_cov\20260603_105646\risk_parity_lw_cov\platform_risk_parity_lw_cov_candidate_20260603_105646`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R001--quant-researcher-5cc36bdb\platform\configs\platform_risk_parity_lw_cov.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R001--quant-researcher-5cc36bdb\platform\results\backtests\risk_parity_lw_cov\20260603_105646\risk_parity\platform_risk_parity_baseline_20260603_105648`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R001--quant-researcher-5cc36bdb\platform\configs\platform_risk_parity.yaml`

## 候选指标
- 累计收益率：59.40%
- 年化收益率：5.71%
- 年化波动率：3.41%
- 最大回撤：-4.37%
- 夏普比率：1.6775
- 年化换手：448191.4181
- 成交笔数：58
- 订单数：58
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：2.39%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0179
- 年化收益率差值：-0.0014
- 年化波动率差值：-0.0010
- 最大回撤差值：0.0000
- 夏普比率差值：0.0090
- 年化换手差值：-1094.5013
- 成交笔数差值：0.0000
- 订单数差值：0.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：-0.0002

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
