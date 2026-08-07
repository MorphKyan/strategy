# 研究报告 r059: 中债30年期国债财富指数 (CBA21801) 替代 511090 ETF 最长周期敏感性测试与收益贡献分析

## 1. 研究背景与核心假设

在国债/多资产风险平价策略研究中，场内 30 年期国债 ETF（如 `511090.SH`）上市时间较短（2023 年 5 月上市，共同历史仅约 3 年），限制了策略在大跨度宏观周期（如 2013 年至 2026 年）下的验证。

**核心假设**：
引入中债 30 年期国债财富（总值）指数（标的代码 `CBA21801`）作为无跟踪误差的久期与收益基准替代 511090 ETF：
1. **历史跨度大幅扩展**：
   - 3 资产组（沪深300ETF + 黄金ETF + 中债30年国债指数）：可测试共同历史从 **2013-07-29** 延伸至 **2026-08-03**（长达 **13.0 年**，共 **3,164 个交易日**）。
   - 6 资产组（红利低波 + 豆粕 + 能化 + 300 + 黄金 + 中债30年国债指数）：可测试共同历史从 **2020-01-17** 延伸至 **2026-08-03**（长达 **6.5 年**，共 **1,583 个交易日**）。
2. **理论基准与实盘可执行配置的双层区分**：
   - **理论研究基准 (`platform/configs/index_benchmark/`)**：用于在大跨度大周期（13.0 年）下验证风险平价算法的无偏差风控与收益特性，指数资产设为可计算收益；
   - **实盘可执行配置 (`platform/configs/capital_100k/`)**：用于实际交易落地，映射到真实场内流动性良好的 ETF 标的（如 `511090.SH`, `510300.SH`, `512890.SH`），完全遵守真实成交量、滑点与交易限制。
3. **Point-in-Time 严谨视角评估**：
   - Black-Litterman 与 Macro Factor 策略全过程采用 `sync_pit_fundamental_views.py` 提供的动态 PIT 基本面/宏观视角数据链（PIT 股息率、PIT 到期收益率、PIT 展期收益率及按国家统计局发布日对齐的 PIT CPI 实际利率），无未来偏差，确保回测具备真正的 Point-in-Time 严谨度。

---

## 2. 方案 A（13.0 年超长全历史）三策略回测全对比 (2014.01.20 ~ 2026.08.03)

严格基于 Thierry Roncalli (2013, 2015, 2016) 论文原著标准参数（Roncalli 2016 第 4 节 EWMA Beta 平滑 $\lambda=0.85$ 与走廊约束；Black-Litterman $\gamma = 0.08$ 倾斜），在 13 年超长历史（**首次真实建仓日 2014-01-20 = 1.0000**）上进行了连续 daily 仿真：

![Option A 13-Year Corrected Comparison](file:///d:/strategy/platform/reports/r059_figures/option_a_13y_full_backtest_comparison.png)

### 方案 A 13.0 年超长全历史 (2014.01.20 ~ 2026.08.03) 真实绩效对比表

| 策略名称 / 论文变体 | 配置文件路径 | 2026.08.03 终点净值 | 13年累计收益率 | 13年年化收益率 | 年化波动率 | 夏普比率 (Sharpe) | 13年最大回撤 (Max DD) | 13年大周期特性评估 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **基本面 Black-Litterman ES** | [`domestic_black_litterman_es_index_benchmark_100k.yaml`](file:///d:/strategy/platform/configs/index_benchmark/domestic_black_litterman_es_index_benchmark_100k.yaml) | **2.5408** | **+154.08%** | **7.72%** | **6.34%** | **0.98** | **-9.32%** | **全场表现最优（年化7.72%/夏普0.98）** |
| **约束平滑 Macro Factor ES** | [`domestic_macro_factor_es_index_benchmark_100k.yaml`](file:///d:/strategy/platform/configs/index_benchmark/domestic_macro_factor_es_index_benchmark_100k.yaml) | **2.4795** | **+147.95%** | **7.51%** | **6.37%** | **0.94** | **-7.52%** | **风控全场最强（最大回撤仅 -7.52%）** |
| **标准 Baseline ES 策略** | [`domestic_baseline_es_index_benchmark_100k.yaml`](file:///d:/strategy/platform/configs/index_benchmark/domestic_baseline_es_index_benchmark_100k.yaml) | **2.4682** | **+146.82%** | **7.47%** | **6.44%** | **0.93** | **-9.33%** | **固定基线基准** |

---

## 3. 公共数据同步工具与 CLI 运行命令行

已按 Hard Rule 9 规范，将指数/期货/PIT宏观数据拉取与更新代码封装进平台公共工具 [`platform/scripts/sync_index_benchmark_data.py`](file:///d:/strategy/platform/scripts/sync_index_benchmark_data.py) 中：

```bash
# 1. 运行公共数据同步工具拉取最新指数/期货/PIT中债收益率数据
.\env\python.exe platform\scripts\sync_index_benchmark_data.py --config platform\configs\index_benchmark\domestic_baseline_es_index_benchmark_100k.yaml

# 2. 运行标准 Baseline ES 指数配置回测
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\index_benchmark\domestic_baseline_es_index_benchmark_100k.yaml --slippage-scenario default

# 3. 运行 Roncalli 2016 第4节 约束平滑 Macro Factor ES 指数配置回测
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\index_benchmark\domestic_macro_factor_es_index_benchmark_100k.yaml --slippage-scenario default

# 4. 运行 Roncalli 2015 严格 PIT 基本面 Black-Litterman ES 指数配置回测
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\index_benchmark\domestic_black_litterman_es_index_benchmark_100k.yaml --slippage-scenario default
```

---

## 4. 结论与实盘建议

1. **13 年超长周期下，论文优化策略全方位超越静态 Baseline**！
2. **双层区分与 PIT 严谨度**：
   - 理论研究验证使用 `index_benchmark` 配置与无未来偏差动态 PIT 视角，展示了算法在无跟踪误差大周期下的真实胜率；
   - 实盘落地推荐使用 `capital_100k` 中的真实 ETF 标的配置（如 `511090.SH`），完全遵守交易流动性与交易限制。


