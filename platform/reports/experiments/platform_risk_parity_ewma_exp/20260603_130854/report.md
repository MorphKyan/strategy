# 平台实验报告：platform_risk_parity_ewma_exp

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-v2-303d9418\platform\results\backtests\platform_risk_parity_ewma_exp\20260603_130854\risk_parity_dynamic_budget\platform_risk_parity_ewma_candidate_20260603_130854`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-v2-303d9418\platform\configs\generated\platform_risk_parity_ewma_candidate.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-v2-303d9418\platform\results\backtests\platform_risk_parity_ewma_exp\20260603_130854\risk_parity_ewma\platform_risk_parity_ewma_baseline_20260603_130855`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-v2-303d9418\platform\configs\platform_risk_parity_ewma.yaml`

## 候选指标
- 累计收益率：60.00%
- 年化收益率：5.76%
- 年化波动率：3.55%
- 最大回撤：-4.10%
- 夏普比率：1.6208
- 年化换手：445685.7419
- 成交笔数：58
- 订单数：59
- 拒单数：1
- 最大待执行意图数：3
- 平均现金权重：4.08%
- 是否有样本外指标：否

## 候选执行拒单
- `insufficient_cash_or_lot`: 1

## Baseline 对比
- 累计收益率差值：0.0005
- 年化收益率差值：0.0000
- 年化波动率差值：0.0009
- 最大回撤差值：-0.0017
- 夏普比率差值：-0.0420
- 年化换手差值：-173871.6388
- 成交笔数差值：-15.0000
- 订单数差值：-14.0000
- 拒单数差值：1.0000
- 最大待执行意图数差值：1.0000
- 平均现金权重差值：0.0118

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
