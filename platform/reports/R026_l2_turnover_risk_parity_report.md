# 基于 L2 正则化权重偏差惩罚与交易成本感知的换手优化风险平价策略实验报告 (R026)

## 1. 实验假设与设计方案 (Hypothesis & Design)

### 1.1 实验背景与核心痛点
在传统的风险平价（Risk Parity）策略中，权重计算通常只关注期末各资产的边际风险贡献（MRC）的对齐，而不考虑从当前持仓（$w_t$）调整到目标持仓（$w_{t+1}$）时所产生的交易换手成本和潜在的过度调仓（Whipsaw Loss）。特别是在市场高波震荡或资产估算协方差矩阵存在噪声时，不考虑调仓摩擦的优化器极易触发微幅但高频的无效交易，从而产生较高的手续费损耗，拖累投资组合的整体业绩表现。

### 1.2 改进假设
为了解决上述调仓摩擦问题，我们设计了 **基于 L2 正则化权重偏差惩罚与交易成本感知的换手优化风险平价策略（L2RegularizedTurnoverRiskParityStrategy）**。
该策略在标准风险平价目标函数中加入了以下两项惩罚：
1. **L2 权重偏差惩罚项**：$\lambda_2 \| w - w_0 \|_2^2$，其中 $w_0$ 是当前持仓权重。此项惩罚目标权重与当前权重的二次偏差，使得权重变化更加平滑，提高优化求解 of 数值鲁棒性，稳定调仓路径。
2. **L1 交易成本感知惩罚项**：$\gamma \| w - w_0 \|_1$，代表交易成本。利用 L1 范数的稀疏性（Sparsity）特征，通过软阈值（Soft-Thresholding）对调仓幅度进行阻尼，过滤微小变动的“噪声调仓”，只有当理论调仓幅度超过阈值时才发生实质性变动。

通过引入上述两项惩罚，策略在数学上转化为如下正则化风险平价求解问题：
$$
\min_{x \ge 0} \quad \frac{1}{2} x^T \Sigma x - \sum_{i=1}^N \ln(x_i) + \frac{\lambda_2}{2 S} \| x - S w_0 \|_2^2 + \gamma \| x - S w_0 \|_1
$$
其中 $S = \sum_{i=1}^N x_i$ 且 $w = x / S$。我们采用 **自适应循环坐标下降算法（Cyclical Coordinate Descent, CCD）** 进行迭代精确求解，在每个坐标轴上对惩罚项应用软阈值算子以获取闭式更新路径。

---

## 2. 实验环境与涉及文件 (Execution Environment & Files)

### 2.1 执行环境
*   **操作系统**：Windows
*   **Python 解释器**：`.\env\python.exe`
*   **平台回测入口**：`platform/scripts/run_platform_backtest.py`
*   **并行回测与分析脚本**：`scratch/run_experiments_r026.py`、`scratch/analyze_results.py`

### 2.2 修改与涉及文件
1.  **策略实现文件**：`platform/src/platform_core/strategy.py`（增量实现 `L2RegularizedTurnoverRiskParityStrategy` 并注册到 `BUILTIN_STRATEGIES`）。
2.  **实验汇总文件**：`platform/results/r026_experiments_summary.json`（保存 26 个配置的全部 IS、OOS 和起点敏感性测试回测指标）。
3.  **非基线研究汇总登记表**：`platform/reports/non_baseline_research_history_summary.md`（登记非基线研究结论与归因）。
4.  **研究成果历史汇总登记表**：`agy-research/research_history_summary.md`（登记本次实验概要与结论）。
5.  **研究看板文件**：`agy-research/research_backlog.md`（更新任务状态）。

---

## 3. 多重对照实验结果总结 (Multi-Comparison Backtest Results)

为了验证该改进在各个配置下的通用性，我们在平台全部 26 个 `baseline_*.yaml` 配置文件下，运行了 Candidate 与 Baseline 的多重对照。

*   **训练/研究样本 (In-Sample, IS)**：从各配置最早可用公共交易日开始，截止至 **2025-06-30**。
*   **最终测试样本 (Out-of-Sample, OOS)**：固定区间为 **2025-07-01** 至 **2026-06-01**。

### 3.1 核心回测指标对比表（Deltas）

以下是 26 个配置文件在 In-Sample (IS) 和 Out-of-Sample (OOS) 下的回测对比结果（Sharpe, Annualized Turnover, Max Drawdown, Trade Count）：

#### 3.1.1 样本内 (In-Sample) 对照结果
| 配置文件名称 | 样本内时段 (IS) | 夏普比率 (B -> C) | 年化换手率 (B -> C) | 最大回撤 (B -> C) | 交易笔数 (B -> C) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `baseline_mvp_equal_weight` | 2017-08-24 至 2025-06-30 | 1.58 -> 1.57 | 0.29 -> 0.26 | -11.23% -> -10.38% | 35 -> 26 |
| `baseline_opt_mvp_equal_weight_risk_parity_ewma` | 2017-08-24 至 2025-06-30 | 2.38 -> 1.57 | 0.53 -> 0.26 | -4.60% -> -10.38% | 53 -> 26 |
| `baseline_opt_r1_domestic_ewma_risk_parity_cvar_dynamic_budget` | 2019-01-18 至 2025-06-30 | 2.38 -> 1.37 | 0.50 -> 0.29 | -3.05% -> -10.38% | 62 -> 31 |
| `baseline_opt_r1_domestic_rolling_risk_parity_cvar_dynamic_budget` | 2019-01-18 至 2025-06-30 | 2.38 -> 1.37 | 0.50 -> 0.29 | -3.05% -> -10.38% | 62 -> 31 |
| `baseline_opt_r2_global_dividend_ewma_risk_parity_cvar_dynamic_budget` | 2019-01-18 至 2025-06-30 | 2.10 -> 1.35 | 0.44 -> 0.29 | -2.71% -> -10.38% | 62 -> 31 |
| `baseline_opt_r2_global_ewma_risk_parity_cvar_dynamic_budget` | 2019-01-18 至 2025-06-30 | 2.08 -> 1.31 | 0.49 -> 0.29 | -2.90% -> -10.38% | 62 -> 31 |
| `baseline_opt_r3_global_nasdaq_all_weather_ewma_risk_parity_cvar_dynamic_budget` | 2020-01-17 至 2025-06-30 | 2.65 -> 2.00 | 0.62 -> 0.44 | -2.25% -> -7.13% | 53 -> 22 |
| `baseline_opt_r5_cvar_dynamic_budget_risk_parity_ewma` | 2017-08-24 至 2025-06-30 | 2.38 -> 1.57 | 0.53 -> 0.26 | -4.60% -> -10.38% | 53 -> 26 |
| `baseline_opt_r6_adaptive_risk_deviation_risk_parity_ewma` | 2017-08-24 至 2025-06-30 | 2.38 -> 1.57 | 0.53 -> 0.26 | -4.60% -> -10.38% | 53 -> 26 |
| `baseline_opt_risk_parity_gerber_risk_parity_lw_cov` | 2017-08-24 至 2025-06-30 | 2.38 -> 1.57 | 0.35 -> 0.26 | -4.60% -> -10.38% | 35 -> 26 |
| `baseline_opt_risk_parity_hrp_risk_parity_ewma` | 2017-08-24 至 2025-06-30 | 2.38 -> 1.57 | 0.53 -> 0.26 | -4.60% -> -10.38% | 53 -> 26 |
| `baseline_opt_risk_parity_lw_cov_risk_parity_ewma` | 2017-08-24 至 2025-06-30 | 2.38 -> 1.57 | 0.53 -> 0.26 | -4.60% -> -10.38% | 53 -> 26 |
| `baseline_opt_us_blend_ewma_risk_parity_cvar_dynamic_budget` | 2019-01-18 至 2025-06-30 | 1.83 -> 1.15 | 0.52 -> 0.31 | -3.07% -> -10.38% | 62 -> 31 |
| `baseline_r1_domestic_ewma` | 2019-01-18 至 2025-06-30 | 1.48 -> 1.37 | 0.56 -> 0.29 | -3.05% -> -10.38% | 62 -> 31 |
| `baseline_r1_domestic_low_vol_ewma` | 2019-01-18 至 2025-06-30 | 1.34 -> 1.25 | 0.44 -> 0.27 | -3.05% -> -10.38% | 62 -> 31 |
| `baseline_r1_domestic_rolling` | 2019-01-18 至 2025-06-30 | 0.98 -> 0.97 | 0.27 -> 0.27 | -10.35% -> -10.38% | 32 -> 33 |
| `baseline_r2_global_dividend_ewma` | 2019-01-18 至 2025-06-30 | 1.14 -> 1.09 | 0.44 -> 0.50 | -9.18% -> -8.62% | 62 -> 65 |
| `baseline_r2_global_ewma` | 2019-01-18 至 2025-06-30 | 1.21 -> 1.23 | 0.50 -> 0.48 | -7.23% -> -6.68% | 72 -> 63 |
| `baseline_r3_global_nasdaq_all_weather_ewma` | 2020-01-17 至 2025-06-30 | 1.74 -> 2.00 | 0.62 -> 0.53 | -3.74% -> -3.51% | 48 -> 25 |
| `baseline_r5_cvar_dynamic_budget` | 2017-08-24 至 2025-06-30 | 1.75 -> 1.57 | 0.42 -> 0.26 | -2.78% -> -4.14% | 53 -> 26 |
| `baseline_r6_adaptive_risk_deviation` | 2017-08-24 至 2025-06-30 | 1.56 -> 1.57 | 0.36 -> 0.26 | -4.61% -> -4.14% | 53 -> 26 |
| `baseline_r7_cluster_representative_damped` | 2024-03-28 至 2025-06-30 | 1.89 -> 1.75 | 1.35 -> 1.44 | -4.10% -> -5.70% | 22 -> 26 |
| `baseline_risk_parity_gerber` | 2017-08-24 至 2025-06-30 | 1.58 -> 1.57 | 0.29 -> 0.26 | -4.60% -> -4.14% | 35 -> 26 |
| `baseline_risk_parity_hrp` | 2017-08-24 至 2025-06-30 | 1.59 -> 1.57 | 0.28 -> 0.26 | -3.72% -> -4.14% | 31 -> 26 |
| `baseline_risk_parity_lw_cov` | 2017-08-24 至 2025-06-30 | 1.58 -> 1.57 | 0.35 -> 0.26 | -4.61% -> -4.14% | 51 -> 26 |
| `baseline_us_blend_ewma` | 2019-01-18 至 2025-06-30 | 0.76 -> 0.79 | 0.48 -> 0.50 | -16.31% -> -15.13% | 67 -> 75 |

#### 3.1.2 样本外 (Out-of-Sample) 最终测试结果
| 配置文件名称 | 样本外时段 (OOS) | 夏普比率 (B -> C) | 年化换手率 (B -> C) | 最大回撤 (B -> C) | 交易笔数 (B -> C) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `baseline_mvp_equal_weight` | 2025-07-01 至 2026-06-01 | 1.58 -> 2.27 | 1.36 -> 1.50 | -11.17% -> -2.71% | 30 -> 13 |
| `baseline_opt_mvp_equal_weight_risk_parity_ewma` | 2025-07-01 至 2026-06-01 | 2.90 -> 2.27 | 1.75 -> 1.50 | -1.77% -> -2.71% | 19 -> 13 |
| `baseline_opt_r1_domestic_ewma_risk_parity_cvar_dynamic_budget` | 2025-07-01 至 2026-06-01 | 2.42 -> 1.67 | 1.41 -> 1.49 | -0.85% -> -3.67% | 14 -> 14 |
| `baseline_opt_r1_domestic_rolling_risk_parity_cvar_dynamic_budget` | 2025-07-01 至 2026-06-01 | 2.42 -> 1.67 | 1.41 -> 1.49 | -0.85% -> -3.67% | 14 -> 14 |
| `baseline_opt_r2_global_dividend_ewma_risk_parity_cvar_dynamic_budget` | 2025-07-01 至 2026-06-01 | 2.03 -> 1.88 | 1.46 -> 1.66 | -1.50% -> -3.18% | 16 -> 15 |
| `baseline_opt_r2_global_ewma_risk_parity_cvar_dynamic_budget` | 2025-07-01 至 2026-06-01 | 2.51 -> 2.13 | 1.56 -> 1.66 | -1.10% -> -3.05% | 28 -> 23 |
| `baseline_opt_r3_global_nasdaq_all_weather_ewma_risk_parity_cvar_dynamic_budget` | 2025-07-01 至 2026-06-01 | 2.91 -> 2.64 | 1.58 -> 1.63 | -0.99% -> -1.64% | 34 -> 26 |
| `baseline_opt_r5_cvar_dynamic_budget_risk_parity_ewma` | 2025-07-01 至 2026-06-01 | 2.90 -> 2.27 | 1.75 -> 1.50 | -1.77% -> -2.71% | 19 -> 13 |
| `baseline_opt_r6_adaptive_risk_deviation_risk_parity_ewma` | 2025-07-01 至 2026-06-01 | 2.90 -> 2.27 | 1.75 -> 1.50 | -1.77% -> -2.71% | 19 -> 13 |
| `baseline_opt_risk_parity_gerber_risk_parity_lw_cov` | 2025-07-01 至 2026-06-01 | 2.71 -> 2.27 | 1.59 -> 1.50 | -1.81% -> -2.71% | 20 -> 13 |
| `baseline_opt_risk_parity_hrp_risk_parity_ewma` | 2025-07-01 至 2026-06-01 | 2.90 -> 2.27 | 1.75 -> 1.50 | -1.77% -> -2.71% | 19 -> 13 |
| `baseline_opt_risk_parity_lw_cov_risk_parity_ewma` | 2025-07-01 至 2026-06-01 | 2.90 -> 2.27 | 1.75 -> 1.50 | -1.77% -> -2.71% | 19 -> 13 |
| `baseline_opt_us_blend_ewma_risk_parity_cvar_dynamic_budget` | 2025-07-01 至 2026-06-01 | 2.51 -> 2.32 | 1.55 -> 1.72 | -1.44% -> -3.19% | 26 -> 27 |
| `baseline_r1_domestic_ewma` | 2025-07-01 至 2026-06-01 | 1.94 -> 2.08 | 1.68 -> 1.60 | -2.90% -> -2.17% | 18 -> 19 |
| `baseline_r1_domestic_low_vol_ewma` | 2025-07-01 至 2026-06-01 | 1.60 -> 1.66 | 1.48 -> 1.42 | -2.51% -> -2.06% | 14 -> 12 |
| `baseline_r1_domestic_rolling` | 2025-07-01 至 2026-06-01 | 1.67 -> 1.67 | 1.49 -> 1.49 | -3.64% -> -3.67% | 13 -> 14 |
| `baseline_r2_global_dividend_ewma` | 2025-07-01 至 2026-06-01 | 2.08 -> 2.12 | 1.54 -> 1.68 | -2.55% -> -2.48% | 14 -> 14 |
| `baseline_r2_global_ewma` | 2025-07-01 至 2026-06-01 | 2.27 -> 2.38 | 1.62 -> 1.72 | -2.74% -> -2.46% | 22 -> 24 |
| `baseline_r3_global_nasdaq_all_weather_ewma` | 2025-07-01 至 2026-06-01 | 2.89 -> 2.85 | 1.84 -> 1.74 | -1.63% -> -1.62% | 31 -> 26 |
| `baseline_r5_cvar_dynamic_budget` | 2025-07-01 至 2026-06-01 | 2.76 -> 2.27 | 1.46 -> 1.50 | -1.27% -> -2.71% | 18 -> 13 |
| `baseline_r6_adaptive_risk_deviation` | 2025-07-01 至 2026-06-01 | 2.31 -> 2.27 | 1.53 -> 1.50 | -2.84% -> -2.71% | 16 -> 13 |
| `baseline_r7_cluster_representative_damped` | 2025-07-01 至 2026-06-01 | 1.40 -> 1.62 | 1.54 -> 1.52 | -4.61% -> -3.33% | 20 -> 16 |
| `baseline_risk_parity_gerber` | 2025-07-01 至 2026-06-01 | 2.29 -> 2.27 | 1.47 -> 1.50 | -2.58% -> -2.71% | 14 -> 13 |
| `baseline_risk_parity_hrp` | 2025-07-01 至 2026-06-01 | 2.32 -> 2.27 | 1.33 -> 1.50 | -1.23% -> -2.71% | 10 -> 13 |
| `baseline_risk_parity_lw_cov` | 2025-07-01 至 2026-06-01 | 2.31 -> 2.27 | 1.53 -> 1.50 | -2.84% -> -2.71% | 16 -> 13 |
| `baseline_us_blend_ewma` | 2025-07-01 至 2026-06-01 | 2.37 -> 2.66 | 1.58 -> 1.78 | -2.63% -> -2.52% | 19 -> 27 |

---

## 4. 起点敏感性测试 (Start-Date Sensitivity Analysis)

我们在训练集（截止至 2025-06-30）内，以最早共同交易日为起跑线，每隔 2 个自然月生成一个新的回测起点 `start_date`，进行滚动起点敏感性测试。

以下是代表性配置的敏感性统计（Sharpe Mean, Sharpe Std, Turnover Mean）：
*   **`baseline_opt_mvp_equal_weight_risk_parity_ewma` (42次运行)**
    *   Baseline 夏普均值: **2.44**, 标准差: **0.58**, 年化换手率均值: **0.97**
    *   Candidate 夏普均值: **2.15**, 标准差: **0.46**, 年化换手率均值: **0.39**
    *   *归因*：虽然 Candidate 年化换手率得到了极其显著的缩减（从 0.97 降至 0.39，降幅约 60%），且夏普的起点标准差更小（0.46），但其牺牲了过多的组合累计收益，导致各起点的夏普中枢大幅降低。
*   **`baseline_r3_global_nasdaq_all_weather_ewma` (27次运行)**
    *   Baseline 夏普均值: **1.77**, 标准差: **0.17**, 年化换手率均值: **0.73**
    *   Candidate 夏普均值: **2.01**, 标准差: **0.15**, 年化换手率均值: **0.76**
    *   *归因*：在该特定全球配置中，起点敏感性测试录得夏普的稳定提升 and 波动降低，表现优异。
*   **`baseline_opt_r1_domestic_ewma_risk_parity_cvar_dynamic_budget` (33次运行)**
    *   Baseline 夏普均值: **2.13**, 标准差: **0.76**, 年化换手率均值: **0.55**
    *   Candidate 夏普均值: **1.74**, 标准差: **0.85**, 年化换手率均值: **0.43**
    *   *归因*：在多资产配置中，Candidate 策略在大部分起点下的表现都出现了退化，且夏普标准差不降反升（从 0.76 升至 0.85），表现不鲁棒。

---

## 5. 过拟合与平庸度评估 (Overfitting & Mediocrity Audit)

根据 `AGENTS.md` 对平台实验的准入审计规约：
1.  **估计有效样本天数审计**：策略在 120 天日线滚动窗口下运行，核心参数有效样本天数为 120天（远大于 30天 限制），满足样本数要求。
2.  **交易摩擦换手率审计**：年化换手率在等权及部分大类配置下有所降低，并未发生严重的换手率暴增，符合不超过 30% 增幅的红线限制。
3.  **策略平庸度与全线优化审计**：
    *   策略仅在少数组合（如美股 NASDAQ 全天候、us_blend）下有局部业绩改善，但在绝大多数配置下出现夏普比率退化和回撤扩大。
    *   在与 CVaR、HRP、Gerber 等高级协方差/预算基准的消融对照下，该策略呈现出全线严重退化的平庸性。
    *   因此，本策略判定为 **“差异不大/局部优势” (No Significant Difference / Local Advantage)**，未能通过平台的全线优化准入要求。

---

## 6. 最终处理动作与结论 (Recommendation & Action)

### 6.1 最终判定
基于上述详尽的多重对照及起点敏感性测试数据，本策略 **未能实现全平台配置的稳健和显著提升**。由于其缺乏底层协方差的高级降噪架构，导致在与精细化优化基线的对比下全线退化。

按照 `AGENTS.md` 的严守硬性规则：
> 只有在全线测试配置下夏普显著提升、无过拟合风险、换手率合理、起点敏感性稳定，并且最终测试样本表现良好时，才判定为“有显著优化”并物理编写策略代码注册并合入主干；若仅在特定资产包表现好、表现平庸、存在过拟合嫌疑、起点敏感性失败或最终测试样本失败，判定为“差异不大/局部优势”或“Failed”，**物理拒绝进入 platform**。严禁在 platform 策略代码中合入、保留或注册任何非显著优化的策略代码，亦严禁新建任何平台配置文件。

### 6.2 处理动作
1.  **物理拒绝合入平台 (Rejection & Clean-up)**：
    由于本策略为“局部优势/Failed”，已彻底将 `L2RegularizedTurnoverRiskParityStrategy` 及其在 `BUILTIN_STRATEGIES` 中的注册代码从 `platform/src/platform_core/strategy.py` 中 **物理还原删除**，保持主干代码库的干净和整洁。
2.  **成果登记 (Registry)**：
    将本次实验量化结果和研究发现登记在非基线成果汇总表 `platform/reports/non_baseline_research_history_summary.md` 以及研究成果历史汇总登记表 `agy-research/research_history_summary.md` 中。
3.  **任务看板状态更新 (Backlog Status)**：
    更新 `agy-research/research_backlog.md` 中任务 R026 的状态为 `Failed` 并标注 Conversation ID 以示完结。
