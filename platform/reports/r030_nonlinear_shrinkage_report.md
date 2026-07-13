# R030: 基于非线性收缩 (Non-linear Shrinkage) 协方差估计的稳健风险平价策略实验报告
报告生成时间: 2026-06-16 14:50:44

## 1. 实验研究背景
在传统的风险平价（RP）或 Ledoit-Wolf 线性收缩（LW）风险平价策略中，协方差矩阵估计是资产配置权重分配的核心输入。
然而，线性收缩估计器将所有样本特征值朝着其均值等比例拉近（线性拉伸校正），这忽略了不同特征值在非线性尺度上的失真差异。
本课题引入基于随机矩阵理论 (RMT) 的非线性收缩协方差估计器 (Non-linear Shrinkage, NLS)，旨在通过对特征值应用非线性谱收缩，
纠正由于样本观测有限导致的高维协方差失真，从而提供更为精准和稳健的风险预算暴露，在降低组合年化换手率的同时提升策略夏普比。

## 2. 实验设置与方法
- **数据区间**:
  - 训练/研究样本区间：最早可用交易日至 `2025-06-30`（含）。
  - 最终测试样本区间 (OOS)：自 `2025-07-01`（含）起。
- **对照实验设计**:
  - 基准策略：各平台配置文件中默认的风险平价策略（如 Ledoit-Wolf 收缩风险平价 `risk_parity_lw_cov` 或是 `cluster_representative_damped_risk_parity` ）。
  - 对照新策略：在对应的协方差估计器中替换为非线性收缩协方差估计 `nonlinshrink.shrink_cov` 的 NLS 稳健风险平价策略。
- **起点敏感性测试**:
  - 从最早可用行情日开始，每 42 个交易日（约 2 个自然月）生成一个起跑点 `start_date`。
  - 每一个起跑点到训练集末端（2025-06-30）的回测长度必须严格大于 3 年（1095 天）。不满足的直接忽略。

## 3. 回测对照实验表现
| 平台配置文件 | 评估阶段 | 策略类型 | 均值/独立 Sharpe | Sharpe Std | 均值/独立 MaxDD | 年化换手率 | 交易笔数 |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `baseline_r0_domestic_equal_weight.yaml` | 样本内 (IS 均值) | 基准 (monthly_equal_weight) | 0.946 | 0.155 | -10.37% | 43.88% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.850 | 0.240 | -2.99% | 28.20% | - |
| | 样本外 (OOS) | 基准 (monthly_equal_weight) | 1.107 | - | -11.19% | 37.70% | 31 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.270 | - | -2.88% | 44.49% | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline_r1_domestic_ewma.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_ewma) | 1.686 | 0.376 | -4.75% | 61.05% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.623 | 0.425 | -5.04% | 51.38% | - |
| | 样本外 (OOS) | 基准 (risk_parity_ewma) | 0.856 | - | -3.71% | 48.03% | 8 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 0.767 | - | -2.28% | 105.82% | 16 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline_r1_domestic_low_vol_ewma.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_ewma) | 2.166 | 0.394 | -3.82% | 54.66% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.807 | 0.461 | -5.23% | 48.85% | - |
| | 样本外 (OOS) | 基准 (risk_parity_ewma) | 0.422 | - | -3.18% | 46.68% | 6 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 0.398 | - | -2.13% | 103.02% | 12 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline_r1_domestic_rolling.yaml` | 样本内 (IS 均值) | 基准 (risk_parity) | 1.499 | 0.449 | -5.43% | 31.68% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.455 | 0.444 | -5.72% | 31.32% | - |
| | 样本外 (OOS) | 基准 (risk_parity) | 1.236 | - | -2.58% | 34.58% | 9 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 0.874 | - | -3.68% | 40.94% | 9 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `global_dividend_ewma.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_lw_cov) | 1.286 | 0.485 | -8.52% | 41.66% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.202 | 0.495 | -8.89% | 46.40% | - |
| | 样本外 (OOS) | 基准 (risk_parity_lw_cov) | 0.705 | - | -2.56% | 99.99% | 13 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 0.772 | - | -2.57% | 166.48% | 16 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `global_ewma.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_lw_cov) | 1.318 | 0.388 | -6.64% | 60.73% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.160 | 0.465 | -7.56% | 56.10% | - |
| | 样本外 (OOS) | 基准 (risk_parity_lw_cov) | 1.305 | - | -2.73% | 103.86% | 20 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 0.917 | - | -2.65% | 163.22% | 21 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline_r5_cvar_dynamic_budget.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_cvar_dynamic_budget) | 2.137 | 0.270 | -2.25% | 33.42% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_cvar_dynamic_budget_nonlinear_shrinkage) | 2.201 | 0.265 | -2.29% | 30.90% | - |
| | 样本外 (OOS) | 基准 (risk_parity_cvar_dynamic_budget) | 1.202 | - | -1.44% | 30.47% | 6 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_cvar_dynamic_budget_nonlinear_shrinkage) | 0.968 | - | -1.39% | 36.49% | 9 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline_r6_adaptive_risk_deviation.yaml` | 样本内 (IS 均值) | 基准 (adaptive_risk_deviation_volatility_triggered) | 1.885 | 0.213 | -2.99% | 35.96% | - |
| | 样本内 (IS 均值) | NLS 新策略 (adaptive_risk_deviation_nonlinear_shrinkage) | 1.874 | 0.236 | -2.96% | 29.48% | - |
| | 样本外 (OOS) | 基准 (adaptive_risk_deviation_volatility_triggered) | 1.338 | - | -3.01% | 52.07% | 9 |
| | 样本外 (OOS) | NLS 新策略 (adaptive_risk_deviation_nonlinear_shrinkage) | 1.117 | - | -2.88% | 28.41% | 6 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline_risk_parity_gerber.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_gerber) | 1.861 | 0.209 | -2.99% | 31.09% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.850 | 0.240 | -2.99% | 28.20% | - |
| | 样本外 (OOS) | 基准 (risk_parity_gerber) | 1.460 | - | -2.85% | 55.03% | 9 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.270 | - | -2.88% | 44.49% | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline_risk_parity_hrp.yaml` | 样本内 (IS 均值) | 基准 (hrp) | 2.093 | 0.306 | -2.89% | 24.74% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.850 | 0.240 | -2.99% | 28.20% | - |
| | 样本外 (OOS) | 基准 (hrp) | 0.017 | - | -1.61% | 0.00% | 0 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.270 | - | -2.88% | 44.49% | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline_risk_parity_lw_cov.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_lw_cov) | 1.876 | 0.213 | -2.99% | 34.90% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.850 | 0.240 | -2.99% | 28.20% | - |
| | 样本外 (OOS) | 基准 (risk_parity_lw_cov) | 1.338 | - | -3.02% | 52.31% | 9 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.270 | - | -2.88% | 44.49% | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `us_blend_ewma.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_lw_cov) | 0.901 | 0.601 | -14.04% | 56.62% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 0.829 | 0.560 | -14.78% | 70.98% | - |
| | 样本外 (OOS) | 基准 (risk_parity_lw_cov) | 1.014 | - | -2.65% | 134.94% | 19 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.006 | - | -2.80% | 179.30% | 24 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `r0_domestic_equal_weight_risk_parity_ewma.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_ewma) | 2.053 | 0.235 | -2.90% | 82.93% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.873 | 0.220 | -2.89% | 37.24% | - |
| | 样本外 (OOS) | 基准 (risk_parity_ewma) | 1.284 | - | -2.75% | 36.90% | 9 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.552 | - | -1.77% | 35.20% | 9 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `r1_domestic_ewma_10y_bond_3x_vol.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_ewma) | 1.240 | 0.236 | -8.33% | 89.80% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.623 | 0.425 | -5.04% | 51.38% | - |
| | 样本外 (OOS) | 基准 (risk_parity_ewma) | 1.174 | - | -5.21% | 85.02% | 15 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 0.767 | - | -2.28% | 105.82% | 16 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `r1_domestic_ewma_risk_parity_cvar_dynamic_budget.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_cvar_dynamic_budget) | 2.012 | 0.382 | -3.37% | 45.40% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_cvar_dynamic_budget_nonlinear_shrinkage) | 2.049 | 0.368 | -3.23% | 43.55% | - |
| | 样本外 (OOS) | 基准 (risk_parity_cvar_dynamic_budget) | 0.900 | - | -1.24% | 24.25% | 8 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_cvar_dynamic_budget_nonlinear_shrinkage) | 0.973 | - | -1.33% | 25.89% | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `r1_domestic_rolling_10y_bond_3x_vol.yaml` | 样本内 (IS 均值) | 基准 (risk_parity) | 1.096 | 0.329 | -9.20% | 46.26% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.455 | 0.444 | -5.72% | 31.32% | - |
| | 样本外 (OOS) | 基准 (risk_parity) | 1.193 | - | -4.75% | 64.88% | 11 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 0.874 | - | -3.68% | 40.94% | 9 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `r2_global_dividend_ewma_risk_parity_cvar_dynamic_budget.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_cvar_dynamic_budget) | 1.385 | 0.636 | -5.95% | 37.11% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_cvar_dynamic_budget_nonlinear_shrinkage) | 1.427 | 0.658 | -5.66% | 40.30% | - |
| | 样本外 (OOS) | 基准 (risk_parity_cvar_dynamic_budget) | 0.721 | - | -1.69% | 27.28% | 7 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_cvar_dynamic_budget_nonlinear_shrinkage) | 0.657 | - | -1.39% | 24.44% | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `r2_global_ewma_risk_parity_cvar_dynamic_budget.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_cvar_dynamic_budget) | 1.430 | 0.593 | -5.70% | 47.48% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_cvar_dynamic_budget_nonlinear_shrinkage) | 1.455 | 0.564 | -5.28% | 43.94% | - |
| | 样本外 (OOS) | 基准 (risk_parity_cvar_dynamic_budget) | 1.021 | - | -1.18% | 28.67% | 10 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_cvar_dynamic_budget_nonlinear_shrinkage) | 0.996 | - | -1.16% | 28.46% | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `risk_parity_gerber_risk_parity_lw_cov.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_lw_cov) | 2.034 | 0.245 | -2.84% | 45.27% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.873 | 0.220 | -2.89% | 37.24% | - |
| | 样本外 (OOS) | 基准 (risk_parity_lw_cov) | 1.548 | - | -1.80% | 37.29% | 9 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_nonlinear_shrinkage) | 1.552 | - | -1.77% | 35.20% | 9 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `us_blend_ewma_risk_parity_cvar_dynamic_budget.yaml` | 样本内 (IS 均值) | 基准 (risk_parity_cvar_dynamic_budget) | 1.048 | 0.811 | -10.61% | 46.88% | - |
| | 样本内 (IS 均值) | NLS 新策略 (risk_parity_cvar_dynamic_budget_nonlinear_shrinkage) | 1.058 | 0.812 | -10.38% | 45.51% | - |
| | 样本外 (OOS) | 基准 (risk_parity_cvar_dynamic_budget) | 1.108 | - | -1.12% | 28.32% | 12 |
| | 样本外 (OOS) | NLS 新策略 (risk_parity_cvar_dynamic_budget_nonlinear_shrinkage) | 0.825 | - | -1.84% | 30.21% | 12 |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 4. 合入验收门槛审计
根据 `research_backlog.md` 中针对 R030 课题的验收门槛定义，我们对实验表现进行审计：

### 4.1 核心审计指标统计:
- **夏普显著提升配置数**: 3 (验收门槛要求 >= 3 个高维或多资产配置 Sharpe 提升 0.08 以上)
- **样本外年化换手率平均变动**: 17.68% (验收门槛要求平均降低 10% 以上, 即 <= -10%)
- **最大单配置换手率反弹幅**: 120.69% (验收门槛要求无任何配置反弹超过 15%)
- **起点敏感性参数稳定性**: 未通过
- [x] **夏普提升门槛**: 满足。
- [ ] **换手率降低门槛**: 未满足 (换手率平均变动为 17.68%, 未达到降 10% 的要求)。
- [ ] **换手率反弹上限**: 未满足 (有配置换手率反弹达到 120.69%, 超过了 15% 门槛限制)。
- [ ] **敏感性波动率门槛**: 未满足。

### 4.2 审计结论:
**判定结果**: **未全面通过验收门槛 (Failed / 局部优势但换手未达标/敏感性未达标)**。
虽然在部分高维组合（如聚类轮动）中夏普有局部上升，但未能全线在换手率或敏感性指标上完全战胜 Ledoit-Wolf 线性收缩基准，或者样本外表现发生衰退。
根据规约，不符合入主干标准，物理拒绝修改 platform 并擦除注册。

**审计异常明细**:
- 配置 `baseline_r0_domestic_equal_weight.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.2395 (门槛 < 0.20), MDD Std = 0.92% (门槛 < 1.5%)
- 配置 `baseline_r1_domestic_ewma.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.4249 (门槛 < 0.20), MDD Std = 2.01% (门槛 < 1.5%)
- 配置 `baseline_r1_domestic_low_vol_ewma.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.4606 (门槛 < 0.20), MDD Std = 2.24% (门槛 < 1.5%)
- 配置 `baseline_r1_domestic_rolling.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.4441 (门槛 < 0.20), MDD Std = 2.32% (门槛 < 1.5%)
- 配置 `global_dividend_ewma.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.4947 (门槛 < 0.20), MDD Std = 2.50% (门槛 < 1.5%)
- 配置 `global_ewma.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.4653 (门槛 < 0.20), MDD Std = 2.26% (门槛 < 1.5%)
- 配置 `baseline_r5_cvar_dynamic_budget.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.2646 (门槛 < 0.20), MDD Std = 0.62% (门槛 < 1.5%)
- 配置 `baseline_r6_adaptive_risk_deviation.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.2355 (门槛 < 0.20), MDD Std = 0.92% (门槛 < 1.5%)
- 配置 `baseline_risk_parity_gerber.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.2395 (门槛 < 0.20), MDD Std = 0.92% (门槛 < 1.5%)
- 配置 `baseline_risk_parity_hrp.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.2395 (门槛 < 0.20), MDD Std = 0.92% (门槛 < 1.5%)
- 配置 `baseline_risk_parity_lw_cov.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.2395 (门槛 < 0.20), MDD Std = 0.92% (门槛 < 1.5%)
- 配置 `us_blend_ewma.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.5597 (门槛 < 0.20), MDD Std = 5.10% (门槛 < 1.5%)
- 配置 `r0_domestic_equal_weight_risk_parity_ewma.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.2199 (门槛 < 0.20), MDD Std = 0.98% (门槛 < 1.5%)
- 配置 `r1_domestic_ewma_10y_bond_3x_vol.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.4249 (门槛 < 0.20), MDD Std = 2.01% (门槛 < 1.5%)
- 配置 `r1_domestic_ewma_risk_parity_cvar_dynamic_budget.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.3685 (门槛 < 0.20), MDD Std = 1.10% (门槛 < 1.5%)
- 配置 `r1_domestic_rolling_10y_bond_3x_vol.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.4441 (门槛 < 0.20), MDD Std = 2.32% (门槛 < 1.5%)
- 配置 `r2_global_dividend_ewma_risk_parity_cvar_dynamic_budget.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.6585 (门槛 < 0.20), MDD Std = 1.92% (门槛 < 1.5%)
- 配置 `r2_global_ewma_risk_parity_cvar_dynamic_budget.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.5641 (门槛 < 0.20), MDD Std = 1.88% (门槛 < 1.5%)
- 配置 `risk_parity_gerber_risk_parity_lw_cov.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.2199 (门槛 < 0.20), MDD Std = 0.98% (门槛 < 1.5%)
- 配置 `us_blend_ewma_risk_parity_cvar_dynamic_budget.yaml` 的起点敏感性指标未达标: Sharpe Std = 0.8116 (门槛 < 0.20), MDD Std = 4.86% (门槛 < 1.5%)