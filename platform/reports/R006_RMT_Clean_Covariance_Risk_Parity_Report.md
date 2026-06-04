# R006 基于随机矩阵理论 (RMT) 特征值清洗的协方差风险平价策略实验报告

## 1. 研究假设与背景 (Hypothesis & Background)
在多资产风险平价策略中，高维资产收益率的样本协方差矩阵（Sample Covariance Matrix）存在明显的历史估算噪声，尤其是当滚动窗口天数 $T$ 与资产数量 $N$ 的比例较小时，协方差矩阵中的特征值极易过度分散（最大特征值被高估，小特征值被低估且可能接近于零）。这会导致风险平价优化器在求解权重时产生样本外的不稳定性，导致过度交易、踏空或回撤控制失效。

本课题基于**随机矩阵理论 (Random Matrix Theory, RMT)**，利用 **Marchenko-Pastur (MP) 分布**对样本相关系数矩阵进行特征值分解，动态求解噪声截止上限：
$$\lambda_+ = \sigma^2 \left(1 + \sqrt{\frac{N}{T}}\right)^2$$
所有低于该上限的特征值判定为随机噪声，并采用**剪切滤波法 (Clipping / Equalization)**，将噪声特征值替换为它们的平均值，在保持迹（对角线元素和）不变的同时滤除历史随机扰动。最后，基于清洗后的相关系数矩阵与样本标准差还原协方差矩阵，使用 Cyclical Coordinate Descent (CCD) 求解风险平价权重。

---

## 2. 更改的文件与运行命令 (Files Changed & Commands)
- **修改文件**：`platform/src/platform_core/strategy.py` (增量实现 `RiskParityRMTCleanStrategy` 类并注册)
- **回测脚本命令**：
  `.\env\python.exe platform/scripts/sync_all_market_data.py` (核对数据时点)
  `.\env\python.exe platform/scripts/run_multicontrast_rmt.py` (对 platform/configs/ 下的所有 10 个配置运行多重对照回测)

---

## 3. 多重对照回测指标变化 (Metrics Delta)

以下为 RMT 特征值清洗策略 (`candidate`) 与各配置文件默认基准策略 (`baseline`) 在对齐区间内回测表现的完整对比：

| 配置文件 (Configuration) | 策略对比 (Baseline -> Candidate) | 夏普比率 (Sharpe Ratio) | 最大回撤 (Max Drawdown) | 年化换手率 (Annualized Turnover) | 换手率变幅 (Turnover Delta) | 成交笔数 (Trade Count) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `baseline_m3m4_fundamental` | `fundamental_value_equal_weight` $\rightarrow$ `rmt_clean` | 0.0000 $\rightarrow$ 3.0361 (+3.0361) | 0.00% $\rightarrow$ -2.64% (-2.64%) | 0.0 $\rightarrow$ 685031.5 | +0.00% | 0 $\rightarrow$ 26 |
| `baseline_mvp_equal_weight` | `monthly_equal_weight` $\rightarrow$ `rmt_clean` | 1.9380 $\rightarrow$ 2.7088 (+0.7708) | -11.14% $\rightarrow$ -4.30% (+6.84%) | 746668.2 $\rightarrow$ 569644.7 | -23.71% | 77 $\rightarrow$ 10 |
| `baseline_r1_domestic_ewma` | `risk_parity_ewma` $\rightarrow$ `rmt_clean` | 1.4750 $\rightarrow$ 1.4337 (-0.0413) | -3.37% $\rightarrow$ -2.65% (+0.72%) | 415426.1 $\rightarrow$ 519911.7 | +25.15% | 37 $\rightarrow$ 46 |
| `baseline_r1_domestic_low_vol_ewma` | `risk_parity_ewma` $\rightarrow$ `rmt_clean` | 1.4357 $\rightarrow$ 1.4590 (+0.0233) | -3.05% $\rightarrow$ -2.33% (+0.73%) | 385808.5 $\rightarrow$ 349477.4 | -9.42% | 26 $\rightarrow$ 30 |
| `baseline_r1_domestic_rolling` | `risk_parity` $\rightarrow$ `rmt_clean` | 1.4039 $\rightarrow$ 1.4829 (+0.0790) | -4.49% $\rightarrow$ -3.43% (+1.06%) | 215895.2 $\rightarrow$ 240064.5 | +11.19% | 16 $\rightarrow$ 20 |
| `baseline_r2_global_dividend_ewma` | `risk_parity_ewma` $\rightarrow$ `rmt_clean` | 1.4589 $\rightarrow$ 1.4894 (+0.0305) | -3.85% $\rightarrow$ -2.86% (+0.99%) | 419758.6 $\rightarrow$ 433486.6 | +3.27% | 37 $\rightarrow$ 42 |
| `baseline_r2_global_ewma` | `risk_parity_ewma` $\rightarrow$ `rmt_clean` | 1.4675 $\rightarrow$ 1.4269 (-0.0406) | -4.18% $\rightarrow$ -3.27% (+0.91%) | 440085.7 $\rightarrow$ 598865.7 | +36.08% | 47 $\rightarrow$ 54 |
| `baseline_r3_global_nasdaq_all_weather_ewma` | `risk_parity_ewma` $\rightarrow$ `rmt_clean` | 1.7068 $\rightarrow$ 1.7740 (+0.0672) | -3.38% $\rightarrow$ -3.69% (-0.31%) | 863320.3 $\rightarrow$ 1083185.6 | +25.47% | 64 $\rightarrow$ 65 |
| `baseline_risk_parity_lw_cov` | `risk_parity_lw_cov` $\rightarrow$ `rmt_clean` | 2.6671 $\rightarrow$ 2.7073 (+0.0402) | -4.51% $\rightarrow$ -4.30% (+0.21%) | 579571.2 $\rightarrow$ 577782.5 | -0.31% | 10 $\rightarrow$ 10 |
| `baseline_us_blend_ewma` | `risk_parity_ewma` $\rightarrow$ `rmt_clean` | 1.4169 $\rightarrow$ 1.4958 (+0.0789) | -4.68% $\rightarrow$ -3.46% (+1.22%) | 426390.5 $\rightarrow$ 709295.0 | +66.35% | 60 $\rightarrow$ 75 |

---

## 4. 过拟合风险与交易摩擦审计 (Overfitting & Turnover Audit)
根据量化策略上线前的硬性过拟合审计标准，进行如下评估：
1. **滚动窗口与样本天数评估**：
   策略在 120 天日线滚动窗口下运行，RMT 噪声特征值方差参数 $\sigma^2$ 估计以及特征分解所依赖的样本天数为 120 天，远大于 30 天的限制门槛，所以在样本量上**不存在过拟合或自由度缺失风险**。
2. **年化换手率变幅评估**：
   审计规则要求 candidate 相较于 baseline 的年化换手率增幅不得大于 **30%**。本策略在多配置对照中表现出明显的换手分化：
   - 在 `baseline_r2_global_ewma` 配置下，换手率从 440,085.7 增至 598,865.7，增幅为 **+36.08%**；
   - 在 `baseline_us_blend_ewma` 配置下，换手率从 426,390.5 增至 709,295.0，增幅为 **+66.35%**。
   这两个配置下换手率增幅明显**超标（均大于 30%）**，说明在高波动的跨境资产或混合配置中，RMT 剪切法会将低特征值直接平均化提高，可能会使投资组合对于资产间微小相关系数变动表现出过高敏感性，导致资产权重在再平衡日发生剧烈漂移，从而带来高昂的交易摩擦成本。

---

## 5. 合入判定与推荐动作 (Recommendation & Action)
- **物理合入判定**：**差异不大/局部优势 (Failed to merge globally)**
  - **判定依据**：本策略在沪深300/红利/国债滚动组合（`baseline_r1_domestic_rolling`，夏普由 1.4039 提升至 1.4829）以及等权重对照组（`baseline_mvp_equal_weight`，夏普由 1.9380 提升至 2.7088）中取得了明显的局部超额业绩。然而，在其余 EWMA 框架的多资产配置下绩效表现一般甚至略有衰退（如 `baseline_r1_domestic_ewma` 的夏普由 1.4750 降至 1.4337）；更致命的是，在 `baseline_r2_global_ewma` 和 `baseline_us_blend_ewma` 中，换手率升幅高达 **36.08%** 和 **66.35%**，明显违反了过拟合和交易费用限制。
- **推荐动作**：
  根据“严禁在 platform 策略代码中合入、保留或注册任何非显著优化的策略代码”的铁律，对本研究策略进行**物理拒绝**：
  1. **擦除策略注册**：执行 `git checkout platform/src/platform_core/strategy.py` 将策略模块彻底恢复至实验前的干净状态，不允许其进入 platform 的策略集合。
  2. **不新建/修改平台配置文件**。
  3. **成果存档**：仅在成果汇总表 `non_baseline_research_history_summary.md` 中记录其指标表现与物理拒绝的归因，本实验报告作为独立文件归档。
