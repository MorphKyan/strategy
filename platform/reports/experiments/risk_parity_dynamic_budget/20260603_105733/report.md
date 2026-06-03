# 平台实验报告：risk_parity_dynamic_budget

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-240c1380\platform\results\backtests\risk_parity_dynamic_budget\20260603_105733\risk_parity_dynamic_budget\platform_risk_parity_dynamic_budget_candidate_20260603_105734`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-240c1380\platform\configs\platform_risk_parity_dynamic_budget.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-240c1380\platform\results\backtests\risk_parity_dynamic_budget\20260603_105733\risk_parity\platform_risk_parity_baseline_20260603_105735`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-240c1380\platform\configs\platform_risk_parity.yaml`

## 候选指标
- 累计收益率：59.99%
- 年化收益率：5.76%
- 年化波动率：3.43%
- 最大回撤：-3.89%
- 夏普比率：1.6773
- 年化换手：433886.2028
- 成交笔数：64
- 订单数：64
- 拒单数：0
- 最大待执行意图数：2
- 平均现金权重：7.25%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.0120
- 年化收益率差值：-0.0009
- 年化波动率差值：-0.0007
- 最大回撤差值：0.0048
- 夏普比率差值：0.0088
- 年化换手差值：-15399.7166
- 成交笔数差值：6.0000
- 订单数差值：6.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：0.0000
- 平均现金权重差值：0.0485

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
