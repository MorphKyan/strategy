# 基于单变量 GARCH 与 Ledoit-Wolf 收缩相关系数的混合协方差风险平价策略评估报告 (R017)

## 1. 研究背景与改进假说
在经典的风险平价（Risk Parity）策略中，资产权重的分配极度依赖于资产协方差矩阵的估计。传统的风险平价多基于滚动样本标准差（即仅考虑逆波动率，忽略资产间相关性），或者基于历史样本协方差矩阵。然而这两种方法存在明显痛点：
1. **时变波动率滞后**：样本标准差或简单的 EWMA 波动率在捕捉金融资产波动率的“时变性”和“波动聚集”（Volatility Clustering）效应时存在时滞，无法在市场风险骤增时及时收缩暴露。
2. **协方差噪声大与不稳定**：直接估计资产间的历史样本协方差矩阵由于受到样本噪声干扰，容易引起等风险贡献权重抖动，进而引发频繁调仓。

**改进假说 (Hypothesis)**：
本研究提出一种**“混合协方差矩阵”风险平价策略 (GARCH-LW)**。具体设想如下：
1. 使用单变量 **GARCH(1,1)** 模型对各资产的历史收益率进行滚动拟合，预测下一期的条件波动率 $\sigma_{i, T+1}$，以更灵敏地反映波动率的时变特征；
2. 使用 **Ledoit-Wolf 收缩方法** 对历史收益率的样本协方差进行收缩，以过滤相关性噪声，并将其转化为相关系数矩阵 $R$；
3. 将两者组合构建混合协方差矩阵 $\Sigma_{i, j} = \sigma_{i, T+1} R_{i, j} \sigma_{j, T+1}$，以此为输入，通过循环坐标下降（CCD）算法求解风险平价权重。
理论上，这能结合 GARCH 对波动聚集的高敏感性与 Ledoit-Wolf 相关矩阵的稳健性，提升资产配置效率，拉升 Sharpe 比率并收紧回撤。

---

## 2. 修改文件与回测命令
为了验证该假说，我们在本地 ETF 数据上执行了多对照回测实验。

### 2.1 修改文件
- `platform/src/platform_core/strategy.py`：增量实现了 `RiskParityGarchLWCovStrategy`（注册名称 `"risk_parity_garch_lw_cov"`），并在 `BUILTIN_STRATEGIES` 中注册（回测验证后已物理清除）。
- `agy-research/research_history_summary.md`：登记实验指标与结论。
- `platform/reports/non_baseline_research_history_summary.md`：登记非基线研究历史成果。

### 2.2 回测执行命令
1. **市场数据同步**：
   `.\env\python.exe platform/scripts/sync_all_market_data.py`
2. **多对照流水线运行**：
   `.\env\python.exe C:\Users\morph\.gemini\antigravity-cli\brain\de1c5e7a-eba1-4230-ac51-4660aef0884b\scratch\run_experiments_pipeline_r017.py`
3. **对照回测单个命令实例**：
   `.\env\python.exe scripts/run_platform_experiment.py --config configs/generated/baseline_mvp_equal_weight_candidate_garch_lw_cov.yaml --baseline-config configs/baseline_mvp_equal_weight.yaml --experiment-name baseline_mvp_equal_weight_exp_garch_lw_cov`

---

## 3. 全线测试配置回测结果对照表
我们在 `2019-02-28`（或各配置的对齐起点）至 `2026-06-01` 区间内，对平台全部 11 个配置文件运行了新策略回测，与 baseline 进行多重对照，结果如下（换手率为年化双边换手率，由 annualized_turnover 除以 1,000,000 换算得到）：

| 测试配置文件 (Config Name) | 运行组别 (Group) | 年化收益率 (Return) | 最大回撤 (MDD) | 夏普比率 (Sharpe) | 年化换手率 (Turnover) | 交易笔数 (Trades) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **baseline_mvp_equal_weight** | baseline | 19.10% | -11.14% | 1.938 | 74.67% | 77.0 |
| | candidate | 10.43% | -3.56% | **2.756** | 134.21% | 32.0 |
| **baseline_m3m4_fundamental** | baseline | 0.00% | 0.00% | 0.000 | 0.00% | 0.0 |
| | candidate | 12.16% | -1.91% | **3.675** | 195.18% | 63.0 |
| **baseline_r1_domestic_rolling** | baseline | 3.56% | -4.49% | 1.404 | 21.59% | 16.0 |
| | candidate | 3.67% | -3.38% | **1.503** | 53.03% | 41.0 |
| **baseline_r1_domestic_ewma** | baseline | 3.75% | -3.37% | 1.475 | 41.54% | 37.0 |
| | candidate | 3.67% | -3.38% | **1.503** | 53.03% | 41.0 |
| **baseline_r1_domestic_low_vol_ewma**| baseline | 3.42% | -3.05% | 1.436 | 38.58% | 26.0 |
| | candidate | 3.44% | -2.90% | **1.448** | 41.41% | 25.0 |
| **baseline_r2_global_ewma** | baseline | 3.99% | -3.08% | **1.552** | 47.90% | 53.0 |
| | candidate | 3.99% | -4.44% | 1.487 | 61.04% | 53.0 |
| **baseline_r2_global_dividend_ewma** | baseline | 3.79% | -2.90% | **1.531** | 46.99% | 37.0 |
| | candidate | 3.84% | -4.22% | 1.458 | 51.14% | 38.0 |
| **baseline_r3_global_nasdaq_all_weather**| baseline | 3.32% | -3.66% | 1.753 | 86.98% | 64.0 |
| | candidate | 3.48% | -2.26% | **1.977** | 108.01% | 74.0 |
| **baseline_us_blend_ewma** | baseline | 4.07% | -3.29% | **1.486** | 56.63% | 57.0 |
| | candidate | 4.25% | -4.45% | 1.484 | 65.91% | 62.0 |
| **baseline_risk_parity_hrp** | baseline | 2.06% | -2.00% | 2.587 | 39.58% | 3.0 |
| | candidate | 3.63% | -3.56% | **2.757** | 136.12% | 32.0 |
| **baseline_risk_parity_lw_cov** | baseline | 3.45% | -4.51% | 2.667 | 57.96% | 10.0 |
| | candidate | 3.63% | -3.56% | **2.757** | 136.12% | 32.0 |

---

## 4. 量化评估与归因分析
根据回测对照数据，我们对该混合协方差风险平价策略进行了全方位的量化审计与归因：

### 4.1 绩效对比归因
1. **等权与局部配置的改进**：
   在标的集中的等权配置组（`baseline_mvp_equal_weight`）和国内纳指全天候（`baseline_r3_global_nasdaq_all_weather_ewma`）下，新策略的 Sharpe 比率实现了显著的跃升（如等权组夏普由 1.938 提升至 2.756），且最大回撤大幅收紧。这是因为 GARCH 能及时捕捉这些标的的波动时变特征，降低了组合的风险暴露。
2. **大类与境外配置的全线性能退化**：
   然而，在多资产滚动及境外资产组合中，新策略出现了**夏普比率退化和回撤扩大**。如全球 EWMA 基准下，夏普从 1.552 下降至 1.487 (-0.065)，回撤由 -3.08% 放大至 -4.44%；全球红利基准下，夏普由 1.531 下降至 1.458 (-0.073)，回撤从 -2.90% 放大至 -4.22%。

### 4.2 换手率摩擦剧增（致命缺陷）
- **审计要求**：换手率较 baseline 的增加幅度不超过 30%。
- **审计结果**：
  在绝大多数配置文件下，Candidate 的换手率增幅都**严重爆表，远超 30%** 的控制红线！
  - `baseline_mvp_equal_weight` 增幅达 **79.7%**；
  - `baseline_r1_domestic_rolling` 增幅达 **145.6%**；
  - `baseline_risk_parity_hrp` 增幅达 **243.9%**；
  - `baseline_risk_parity_lw_cov` 增幅达 **134.8%**；
- **致命成因分析**：
  GARCH 模型在估计下一期条件波动率时，会基于前一期的收益率残差 $\epsilon_t$ 与条件方差 $\sigma_t^2$ 进行非线性递推。由于金融市场日频波动存在较强的随机噪声，GARCH 预测的条件波动率极易发生频繁、较大幅度的摆动。这导致等风险贡献计算出的目标权重每天都在进行微调，从而在回测中产生高频调仓。高换手率会带来极高的实盘交易成本，直接吞噬超额收益，不具备实盘落地可行性。

### 4.3 样本估计与过拟合审计
- **审计要求**：120天日线滚动窗口下，核心参数估计或风险 MRC 计算的有效样本天数不少于 30 天。
- **审计结果**：
  我们强制限定了 `min_periods` 至少为 30 天，确保了有效估计窗口在 30 天以上。但是，由于 GARCH 参数（$\omega, \alpha, \beta$）在短滚动窗口（120天）下的估计对局部极端收益极其敏感，拟合得到的模型稳定性极差，在样本外存在极高的参数过拟合与噪声放大风险。

---

## 5. 实验结论与推荐建议
- **最终结论**：**Failed (失败) / 物理拒绝**
- **归因总结**：
  混合协方差策略未能满足“全线配置夏普显著提升”和“换手率增幅不超过30%”的双重红线。策略在部分全球/红利资产配置上出现了绩效退化，且由于 GARCH 条件标准差的时变高敏感性，导致资产权重过度调整，年化换手率最高暴增 243.9%。
- **动作执行**：
  我们已按照严格的研究规范执行**物理拒绝**：
  1. 已使用 `git restore` 彻底回滚并擦除了 `platform/src/platform_core/strategy.py` 中的所有代码修改，仓库不留存该策略实现；
  2. 未新增任何平台 yaml 配置文件；
  3. 将所有的研究参数、回测指标及被拒原因详细地记录于非基线研究历史汇总表 `platform/reports/non_baseline_research_history_summary.md` 和成果历史登记表 `agy-research/research_history_summary.md` 中。
