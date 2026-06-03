# 平台实验报告：platform_mvp_exp

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-v2-303d9418\platform\results\backtests\platform_mvp_exp\20260603_130846\risk_parity_dynamic_budget\platform_mvp_candidate_20260603_130846`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-v2-303d9418\platform\configs\generated\platform_mvp_candidate.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-v2-303d9418\platform\results\backtests\platform_mvp_exp\20260603_130846\monthly_equal_weight\platform_mvp_baseline_20260603_130847`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-v2-303d9418\platform\configs\platform_mvp.yaml`

## 候选指标
- 累计收益率：22.38%
- 年化收益率：10.99%
- 年化波动率：10.17%
- 最大回撤：-10.14%
- 夏普比率：1.0812
- 年化换手：1073795.9117
- 成交笔数：16
- 订单数：16
- 拒单数：0
- 最大待执行意图数：0
- 平均现金权重：41.06%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：0.0528
- 年化收益率差值：0.0250
- 年化波动率差值：-0.0662
- 最大回撤差值：0.1295
- 夏普比率差值：0.5752
- 年化换手差值：96765.0110
- 成交笔数差值：-34.0000
- 订单数差值：-34.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：-1.0000
- 平均现金权重差值：0.2304

## 建议
- 接受

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
