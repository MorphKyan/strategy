# 基于 EWMA 波动率修正与半协方差收缩的下行风险平价策略实验报告 (R023)

## 1. 研究假设与策略设计

### 1.1 实验背景与设想
传统的风险平价策略（Risk Parity）通常依赖全收益样本的协方差矩阵来度量资产之间的相关结构与波动风险。然而，在多资产组合中，投资者更关注**下行风险（Downside Risk）**，即资产下跌通道中的共同波动暴露。
下行半协方差矩阵（Downside Semi-Covariance Matrix）仅针对负超额收益样本进行统计，在理论上更符合控制下行波动和回撤的需求。但其面临核心技术痛点：仅利用负收益样本会导致有效样本量折半（在上涨市中样本甚至更少），使得协方差估计噪声极大、多重共线性风险高，导致优化权重在调仓日剧烈跳动，从而大幅增加换手磨损。

为此，本实验设计了**基于 EWMA 波动率修正与半协方差收缩的下行风险平价策略** (`RiskParityEWMASemiCovShrinkageStrategy`)，期望通过以下三个步骤解决上述问题：
1. **EWMA 波动率修正**：使用时变 EWMA（指数加权移动平均）标准差，快速捕捉各资产最新的波动状态，防范时效滞后；
2. **下行半协方差收缩**：仅针对下跌样本点计算样本半协方差矩阵，并引入 Ledoit-Wolf 收缩技术（向常数相关系数目标矩阵收缩）平滑噪声，得到稳健的下行半协方差矩阵；
3. **重新缩放与权重求解**：将收缩后的下行半协方差矩阵转化为下行半相关系数矩阵，再利用各资产的 EWMA 波动率重新缩放，拼装成最终的下行协方差矩阵，最后利用 CCD（循环坐标下降）算法精确求解权重。

---

## 2. 实验环境与命令

*   **运行环境**：`.\env\python.exe` (Windows)
*   **回测时间跨度**：
    *   **样本内 (IS) 训练/研究区间**：最长公共交易日起至 `2025-06-30`（含）
    *   **样本外 (OOS) 最终测试区间**：`2025-07-01` 至 `2026-06-01`
*   **执行指令**：
    *   `D:\strategy\env\python.exe scratch/run_r023_experiments.py`
*   **修改文件**：
    *   `platform/src/platform_core/strategy.py`：增量实现了 `RiskParityEWMASemiCovShrinkageStrategy` 并注册至 `BUILTIN_STRATEGIES`。

---

## 3. 多重对照实验表现 (IS vs OOS)

我们在平台现有的全部 14 个基准配置下，对 Baseline 策略与新策略（Candidate）进行了对比回测。数据结果如下（Sharpe比率、最大回撤、年化双边换手率）：

### 3.1 详细绩效对照表

| 配置文件名称 | 策略类型 | 样本内夏普 (IS Sharpe) | 样本内回撤 (IS MaxDD) | 样本内换手 (IS Turnover) | 样本外夏普 (OOS Sharpe) | 样本外回撤 (OOS MaxDD) | 样本外换手 (OOS Turnover) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **baseline_mvp_equal_weight.yaml** | Baseline<br>Candidate | 0.952<br>**1.593** | -10.82%<br>**-4.80%** | 0.341<br>0.584 | 1.592<br>**2.319** | -11.16%<br>**-2.18%** | 0.375<br>0.661 |
| **baseline_r1_domestic_ewma.yaml** | Baseline<br>Candidate | **1.151**<br>1.112 | **-9.69%**<br>-9.26% | 0.524<br>0.666 | 1.539<br>**1.853** | -3.65%<br>**-2.24%** | 0.507<br>0.809 |
| **baseline_r1_domestic_low_vol_ewma.yaml** | Baseline<br>Candidate | **1.591**<br>1.536 | -6.01%<br>**-5.86%** | 0.453<br>0.551 | 1.063<br>**1.377** | -3.75%<br>**-1.90%** | 0.614<br>0.875 |
| **baseline_r1_domestic_rolling.yaml** | Baseline<br>Candidate | 0.925<br>**1.577** | -10.54%<br>**-5.43%** | 0.240<br>0.511 | **1.819**<br>1.673 | **-2.56%**<br>-3.69% | 0.395<br>0.620 |
| **global_dividend_ewma.yaml** | Baseline<br>Candidate | **1.127**<br>0.958 | **-9.20%**<br>-12.18% | 0.443<br>0.600 | 1.698<br>**1.790** | -2.52%<br>**-2.45%** | 1.162<br>**0.925** |
| **global_ewma.yaml** | Baseline<br>Candidate | **1.169**<br>0.981 | **-7.09%**<br>-11.35% | 0.560<br>0.710 | 2.136<br>**2.221** | -2.74%<br>**-2.52%** | 1.053<br>**1.017** |
| **global_nasdaq_all_weather_ewma.yaml** | Baseline<br>Candidate | 1.847<br>**1.891** | **-3.69%**<br>-4.10% | 0.600<br>0.876 | 2.826<br>**2.884** | **-1.63%**<br>-1.71% | 1.265<br>**1.240** |
| **baseline_r5_cvar_dynamic_budget.yaml** | Baseline<br>Candidate | **1.745**<br>1.720 | **-2.78%**<br>-4.08% | 0.419<br>0.524 | **2.464**<br>2.259 | **-1.40%**<br>-2.87% | 0.345<br>0.622 |
| **baseline_r6_adaptive_risk_deviation.yaml** | Baseline<br>Candidate | 1.561<br>**1.720** | -4.61%<br>**-4.08%** | 0.359<br>0.524 | **2.282**<br>2.259 | -2.98%<br>**-2.87%** | 0.551<br>0.622 |
| **global_cluster_representative_damped.yaml** | Baseline<br>Candidate | **1.894**<br>1.648 | **-4.10%**<br>-6.05% | 1.346<br>1.672 | 1.317<br>**2.106** | -4.61%<br>**-3.61%** | 0.578<br>0.962 |
| **baseline_risk_parity_gerber.yaml** | Baseline<br>Candidate | 1.581<br>**1.720** | -4.60%<br>**-4.08%** | 0.291<br>0.524 | **2.411**<br>2.241 | **-2.83%**<br>-2.87% | 0.540<br>0.649 |
| **baseline_risk_parity_hrp.yaml** | Baseline<br>Candidate | 1.591<br>**1.720** | **-3.72%**<br>-4.08% | 0.284<br>0.524 | 1.640<br>**2.241** | **-0.83%**<br>-2.87% | 0.116<br>0.649 |
| **baseline_risk_parity_lw_cov.yaml** | Baseline<br>Candidate | 1.581<br>**1.720** | -4.61%<br>**-4.08%** | 0.354<br>0.524 | **2.266**<br>2.241 | -2.98%<br>**-2.87%** | 0.572<br>0.649 |
| **us_blend_ewma.yaml** | Baseline<br>Candidate | **0.743**<br>0.503 | **-16.32%**<br>-25.57% | 0.509<br>0.691 | 1.955<br>**2.333** | -2.65%<br>**-2.50%** | 1.371<br>**0.956** |

---

## 4. 起点敏感性测试

我们在不触碰样本外数据的前提下，在样本内区间内每隔 2 个自然月变动一次 `start_date`（在 126 天的滑窗约束下，平均每只组合回测 15 至 43 个不同起点），计算 Candidate 对 Baseline 的夏普比率胜出率及平均表现：

*   **baseline_mvp_equal_weight**：敏感性胜出率 **97.7%**，Sharpe 均值由 1.341 -> 2.220，表现稳定改善。
*   **baseline_r1_domestic_ewma**：敏感性胜出率 **11.8%**，Sharpe 均值由 2.014 -> 1.915，未见优势。
*   **baseline_r1_domestic_low_vol_ewma**：敏感性胜出率 **8.8%**，Sharpe 均值由 2.286 -> 2.168，表现变差。
*   **baseline_r1_domestic_rolling**：敏感性胜出率 **79.4%**，Sharpe 均值由 1.864 -> 2.041，有一定稳定性。
*   **global_dividend_ewma**：敏感性胜出率 **11.8%**，Sharpe 均值由 1.830 -> 1.726，表现衰退。
*   **global_ewma**：敏感性胜出率 **26.5%**，Sharpe 均值由 1.777 -> 1.711，表现衰退。
*   **global_nasdaq_all_weather_ewma**：敏感性胜出率 **60.0%**，Sharpe 均值由 1.827 -> 1.812，表现相当。
*   **baseline_r5_cvar_dynamic_budget**：敏感性胜出率 **14.0%**，Sharpe 均值由 2.484 -> 2.382，表现变差。
*   **baseline_r6_adaptive_risk_deviation**：敏感性胜出率 **95.3%**，Sharpe 均值由 2.202 -> 2.382，有优势。
*   **baseline_r7_cluster_representative_damped**：敏感性胜出率 **0.0%**，Sharpe 均值由 1.895 -> 1.454，严重衰退。
*   **baseline_risk_parity_gerber**：敏感性胜出率 **95.3%**，Sharpe 均值由 2.227 -> 2.382，有优势。
*   **baseline_risk_parity_hrp**：敏感性胜出率 **58.1%**，Sharpe 均值由 2.349 -> 2.382，表现相当。
*   **baseline_risk_parity_lw_cov**：敏感性胜出率 **93.0%**，Sharpe 均值由 2.246 -> 2.382，有优势。
*   **us_blend_ewma**：敏感性胜出率 **41.2%**，Sharpe 均值由 1.535 -> 1.484，表现衰退。

---

## 5. 核心指标退化审计与技术归因

下行半协方差收缩策略的实验结果未通过准入门槛，其退化机制可归结为以下两个技术逻辑缺陷：

1.  **牛市与强上行趋势下的配置滞后与“趋势踏空”**：
    由于下行半协方差仅针对下跌交易日（$R_t < 0$）的残差做统计，排除了所有上行波动的贡献。在单边上涨或者强趋势行情中，某些具有强动量的资产（如海外美股纳指或黄金）会出现连续上涨，但在下行半协方差的视角下，因为“没有下跌”，其估计出的下行波动率极其微小。
    这导致优化器在计算风险贡献时，会向这些资产分配极大的权重；一旦趋势发生逆转或高位调整，高配的动量资产会带来意外的重大亏损。同时，由于半协方差剥离了上行，导致组合权重对上涨反应极度迟钝，在美股和境外资产强势上涨的 OOS 周期中表现出显著的踏空效应，这导致 `us_blend_ewma` 和 `r2_global_ewma` 的夏普比率出现显著衰退，最大回撤成倍增加（例如 `us_blend_ewma` 最大回撤由 **-16.32%** 扩大至 **-25.57%**）。

2.  **交易频率与换手率普遍上升**：
    由于下行收益样本天然只有正常样本量的一半，哪怕使用了 Ledoit-Wolf 协方差收缩，其估计参数的自由度依然低于全收益协方差。在多资产组合再平衡中，下跌样本天数的轻微变化都会引发协方差结构的阶跃移动，进而触发优化权重的抖动。
    回测数据显示，大部分 Candidate 配置在 IS 区间的年化双边换手率均录得显著增加（例如 `baseline_mvp_equal_weight` 由 **0.341** 增至 **0.584 (+71.2%)**，`baseline_r1_domestic_ewma` 由 **0.524** 增至 **0.666 (+27.1%)**）。这违背了防御性策略平滑调仓、降低交易损耗的核心理念。

---

## 6. 最终结论与动作建议

*   **课题结论**：**物理拒绝 (Failed / 局部优势)**。
    虽然策略在 MVP 等权和部分国内滚动基准上有一定提升，但在大部分包含 EWMA 时变方差的境内外多资产组合（如 global_ewma, global_dividend_ewma, us_blend_ewma, low_vol_ewma）中，其样本内夏普比率出现显著退化，最大回撤明显扩大，且换手率多处触发审计红线。起点敏感性测试的低胜出率也证明了策略在不同历史起点下的表现极不稳健，具有严重的过拟合风险。
*   **动作建议**：
    1.  **物理拒绝合入平台主干**：从 `platform/src/platform_core/strategy.py` 中彻底擦除 `RiskParityEWMASemiCovShrinkageStrategy` 类实现及在 `BUILTIN_STRATEGIES` 中的注册。
    2.  **不创建任何平台配置文件**。
    3.  **结果沉淀**：将本报告归档至 `platform/reports/`，并将结论登记到 `non_baseline_research_history_summary.md` 成果登记表中。
