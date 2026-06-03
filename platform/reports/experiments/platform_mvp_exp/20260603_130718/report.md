# 平台实验报告：platform_mvp_exp

## 目标
运行标准化平台实验，并在 baseline 可用时进行对比。

## 产物
- 候选原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-v2-303d9418\platform\results\backtests\platform_mvp_exp\20260603_130718\risk_parity_dynamic_budget\platform_mvp_candidate_20260603_130718`
- 候选配置：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-v2-303d9418\platform\configs\generated\platform_mvp_candidate.yaml`
- Baseline 原始结果路径：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-v2-303d9418\platform\results\backtests\platform_mvp_exp\20260603_130718\monthly_equal_weight\platform_mvp_baseline_20260603_130719`
- Baseline 配置：`C:\Users\morph\.gemini\antigravity-cli\brain\419e7723-6b9d-45aa-a98c-cfd5ad22f4bd\.system_generated\worktrees\subagent-Quant-Researcher--R003--quant-researcher-v2-303d9418\platform\configs\platform_mvp.yaml`

## 候选指标
- 累计收益率：-0.79%
- 年化收益率：-0.41%
- 年化波动率：7.15%
- 最大回撤：-10.14%
- 夏普比率：-0.0570
- 年化换手：553796.4368
- 成交笔数：8
- 订单数：8
- 拒单数：0
- 最大待执行意图数：0
- 平均现金权重：71.36%
- 是否有样本外指标：否

## Baseline 对比
- 累计收益率差值：-0.1789
- 年化收益率差值：-0.0890
- 年化波动率差值：-0.0963
- 最大回撤差值：0.1294
- 夏普比率差值：-0.5630
- 年化换手差值：-423234.4638
- 成交笔数差值：-42.0000
- 订单数差值：-42.0000
- 拒单数差值：0.0000
- 最大待执行意图数差值：-1.0000
- 平均现金权重差值：0.5334

## 建议
- 继续改进

## 说明
- 指标根据平台生成的 CSV 产物计算。
- 执行约束影响来自 `orders.csv`、`trades.csv` 和 `nav.csv` 中的待执行意图状态。
