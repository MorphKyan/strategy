# R011 基于下行半协方差的稳健风险平价策略实验报告

## 1. 研究假设与背景 (Hypothesis & Background)
传统的风险平价（Risk Parity）策略通常依赖资产的完整历史波动率或协方差矩阵来进行风险预算的分配。然而，从投资者的心理偏好和实际回撤控制要求来看，上行波动（盈利带来的波动）并不属于真实风险，只有下行波动（资产下跌带来的亏损风险）才应当被度量。

本研究提出基于**下行半协方差（Downside Semi-Covariance）**的稳健风险平价策略。该策略仅利用资产收益率低于预设目标收益率（通常为 0）的样本天数来计算下行半协方差矩阵，以求在投资组合优化中更精确地识别和规避“资产共同下跌”的系统性下行风险。
为了克服因为仅保留下行区间样本导致的样本量减半（如 120 天中仅有约 60 天）、历史噪声估计过大以及共线性导致的矩阵非正定问题，本策略引入了**对角线收缩技术（Diagonal Shrinkage）**，通过融入对角目标矩阵来平滑估计，构建稳健的下行半协方差估计。最后，使用循环坐标下降法（CCD）迭代求解等风险贡献下的投资权重。

---

## 2. 更改的文件与运行命令 (Files Changed & Commands)
- **修改文件**：`platform/src/platform_core/strategy.py` (增量实现 `RiskParitySemiCovStrategy` 类并注册到 `BUILTIN_STRATEGIES`，其键名为 `"risk_parity_semi_cov"`)。
- **运行命令**：
  `.\env\python.exe -u .\run_experiments_pipeline_r011.py` (在本地工作区环境下，对 platform/configs/ 下的所有 11 个配置运行多重对照回测)

---

## 3. 多重对照回测指标变化 (Metrics Delta)

以下为基于下行半协方差的稳健风险平价策略 (`candidate`) 与各配置文件默认基准策略 (`baseline`) 在对齐区间内回测表现的完整对比：

| 配置文件 (Configuration) | 策略对比 (Baseline -> Candidate) | 夏普比率 (Sharpe Ratio) | 最大回撤 (Max Drawdown) | 年化换手率 (Annualized Turnover) | 换手率变幅 (Turnover Delta) | 成交笔数 (Trade Count) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `baseline_mvp_equal_weight` | `monthly_equal_weight` $\rightarrow$ `candidate` | 1.938 $\rightarrow$ 2.491 (+0.553) | -11.14% $\rightarrow$ -3.59% | 746.67% $\rightarrow$ 852.26% | +14.14% | 77 $\rightarrow$ 26 |
| `baseline_m3m4_fundamental` | `fundamental_value_equal` $\rightarrow$ `candidate` | 0.000 $\rightarrow$ 3.109 (+3.109) | 0.00% $\rightarrow$ -2.49% | 0.00% $\rightarrow$ 754.93% | N/A | 0 $\rightarrow$ 29 |
| `baseline_r1_domestic_rolling` | `risk_parity` $\rightarrow$ `candidate` | 1.404 $\rightarrow$ 1.294 (-0.110) | -4.49% $\rightarrow$ -3.73% | 215.90% $\rightarrow$ 311.78% | +44.41% | 16 $\rightarrow$ 33 |
| `baseline_r1_domestic_ewma` | `risk_parity_ewma` $\rightarrow$ `candidate` | 1.475 $\rightarrow$ 1.294 (-0.181) | -3.37% $\rightarrow$ -3.73% | 415.43% $\rightarrow$ 311.78% | -24.95% | 37 $\rightarrow$ 33 |
| `baseline_r1_domestic_low_vol` | `risk_parity_ewma` $\rightarrow$ `candidate` | 1.436 $\rightarrow$ 1.385 (-0.051) | -3.05% $\rightarrow$ -3.54% | 385.81% $\rightarrow$ 238.56% | -38.17% | 26 $\rightarrow$ 21 |
| `baseline_r2_global_ewma` | `risk_parity_ewma` $\rightarrow$ `candidate` | 1.552 $\rightarrow$ 1.369 (-0.183) | -3.08% $\rightarrow$ -4.27% | 479.04% $\rightarrow$ 328.42% | -31.44% | 53 $\rightarrow$ 33 |
| `baseline_r2_global_dividend` | `risk_parity_ewma` $\rightarrow$ `candidate` | 1.531 $\rightarrow$ 1.365 (-0.166) | -2.90% $\rightarrow$ -4.03% | 469.96% $\rightarrow$ 302.74% | -35.58% | 37 $\rightarrow$ 28 |
| `baseline_r3_global_nasdaq_aw` | `risk_parity_ewma` $\rightarrow$ `candidate` | 1.753 $\rightarrow$ 1.783 (+0.030) | -3.66% $\rightarrow$ -2.22% | 869.82% $\rightarrow$ 645.13% | -25.83% | 64 $\rightarrow$ 61 |
| `baseline_us_blend_ewma` | `risk_parity_ewma` $\rightarrow$ `candidate` | 1.486 $\rightarrow$ 1.355 (-0.131) | -3.29% $\rightarrow$ -4.10% | 566.26% $\rightarrow$ 372.20% | -34.27% | 57 $\rightarrow$ 63 |
| `baseline_risk_parity_hrp` | `hrp` $\rightarrow$ `candidate` | 2.587 $\rightarrow$ 2.487 (-0.100) | -2.00% $\rightarrow$ -3.59% | 395.81% $\rightarrow$ 864.43% | +118.39% | 3 $\rightarrow$ 26 |
| `baseline_risk_parity_lw_cov` | `risk_parity_lw_cov` $\rightarrow$ `candidate` | 2.667 $\rightarrow$ 2.487 (-0.180) | -4.51% $\rightarrow$ -3.59% | 579.57% $\rightarrow$ 864.43% | +49.15% | 10 $\rightarrow$ 26 |

*注：为了数据展示的常规性，表格中的换手率在 pipeline 原生输出的基础上进行了 1/100 的换算，以还原常规百分比单位。*

---

## 4. 过拟合风险与交易摩擦审计 (Overfitting & Turnover Audit)
1. **滚动窗口与有效样本天数**：
   在 120 天日线滚动窗口下，本策略通过 `returns < 0` 过滤下行区间。在回测历史时段内，各标的日均下跌概率接近 50%，对应 120 天的有效下行样本约为 60 天左右，多于 30 天的自由度限制门槛，基本符合过拟合审计中对样本量自由度的基本限制。
2. **年化换手率与交易摩擦变幅**：
   开发规约硬性要求 candidate 的换手率增幅不得大于 **30%**。然而，多配置对照结果显示：
   - 在国内基础配置 `baseline_r1_domestic_rolling` 下，年化换手率增幅达到了 **+44.41%**，成交笔数翻倍（16 笔增至 33 笔）。
   - 在与高性能基准策略 `hrp` 与 `lw_cov` 的对照中，由于半协方差仅利用下行偏离导致权重波动较敏感，换手率分别暴增了 **+118.39%** 和 **+49.15%**。
   - 这表明在部分市场组合中，由于忽略了上行波动，下行半协方差的估计在某些资产反弹或震荡分化时，会导致更剧烈的权重调整和过度调仓，产生严重的交易摩擦，**未能通过交易摩擦审计要求**。

---

## 5. 判定结论与推荐动作 (Recommendation & Action)
- **判定结论**：**差异不大/局部优势 (Merge Rejected - Failed)**
  - **判定依据**：虽然该策略在窄幅等权配置（如 MVP、基本面过滤等）和 Nasdaq 全天候低波组合中表现出一定的回撤控制效果（最大回撤显著收缩）和夏普提升，但是在**几乎所有使用 EWMA 波动估计的多资产及跨境配置中，夏普比率均发生了全线下降（降幅介于 -0.05 至 -0.18 之间）**。同时在 `domestic_rolling`, `hrp`, `lw_cov` 组合中触发了换手率增幅大于 30% 的交易摩擦审计红线。这证明仅度量下行波动的半协方差估计并不能在多资产大涨的趋势行情中取得稳定优势，且极易引发过度调仓磨损。
- **推荐动作**：
  根据量化开发规约的最高准则，由于未能满足“全线测试配置夏普全线提升且无过拟合嫌疑”的上线要求，**物理拒绝该策略合入主干**：
  1. **完全清除策略代码**：必须从 `platform/src/platform_core/strategy.py` 中彻底清除本次研究所实现的 `RiskParitySemiCovStrategy` 类及相关的字典注册，保持主干代码不受污染。
  2. **不新增任何 yaml 配置文件**。
  3. **登记研究历史**：物理删除代码后，仅在成果汇总表 `non_baseline_research_history_summary.md` 登记本次研究的实证数据和结论，并在看板 `agy-research/research_backlog.md` 中将该课题移入已完成并标记结论。

报告撰写完毕。
