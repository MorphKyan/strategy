# agri_energy 同起点诊断报告

## 目标

围绕 `agri_energy` 做下一轮诊断，不扩展 universe，不做参数搜索。用 `2020-01-17` 至 `2026-05-19` 对 baseline 和 `agri_energy` 做同起点比较，并检查 `agri_energy` 的权重路径、交易明细、`511260` 长期集中度和商品袖子收益贡献。

## 方法

research 的 `main.py` 当前加载数据后不会按 config 中的 `backtest.start_date` / `backtest.end_date` 截断，所以本轮没有通过改 YAML 伪造同起点实验。诊断方式是在内存中用 `DataHandler.load_etf_data(..., auto_fetch=False)` 加载本地后复权数据，显式切片到 `2020-01-17` 至 `2026-05-19`，然后分别调用 `risk_parity.run_strategy(df, config)` 重新起跑 baseline 和 `agri_energy`。

本轮使用的配置：

- Baseline：`research/configs/risk_parity.yaml`
- 候选：`research/configs/generated/risk_parity_etfsel_agri_energy_20260531.yaml`

生成的诊断产物：

- `research/reports/experiments/agri_energy_same_start_20260531/diagnostics.json`
- `research/reports/experiments/agri_energy_same_start_20260531/baseline_same_start_backtest_results.csv`
- `research/reports/experiments/agri_energy_same_start_20260531/baseline_same_start_trade_history.csv`
- `research/reports/experiments/agri_energy_same_start_20260531/agri_energy_same_start_backtest_results.csv`
- `research/reports/experiments/agri_energy_same_start_20260531/agri_energy_same_start_trade_history.csv`

仓库当前没有样本外指标，`oos_metrics_available=false`。

## 同起点指标

| 指标 | Baseline 同起点 | `agri_energy` 同起点 | 差值 |
|---|---:|---:|---:|
| start_date | 2020-01-17 | 2020-01-17 | - |
| end_date | 2026-05-19 | 2026-05-19 | - |
| observations | 1531 | 1531 | 0 |
| total_return | 40.08% | 54.23% | +14.15 pct |
| annualized_return | 5.71% | 7.40% | +1.69 pct |
| annualized_volatility | 3.57% | 4.08% | +0.50 pct |
| max_drawdown | -4.08% | -4.01% | +0.07 pct |
| sharpe_ratio | 1.5969 | 1.8149 | +0.2180 |
| annualized_turnover | 0.3936 | 0.5820 | +0.1885 |
| trade_count | 27 | 65 | +38 |

同起点后，`agri_energy` 的收益、Sharpe 和最大回撤优势仍然存在，说明上一轮优势不是单纯由 baseline 更早起点造成。但换手和交易笔数明显上升，执行复杂度是主要代价。

## 权重路径诊断

| 权重项 | Baseline 均值 | Baseline 中位数 | Baseline 最大值 | `agri_energy` 均值 | `agri_energy` 中位数 | `agri_energy` 最大值 |
|---|---:|---:|---:|---:|---:|---:|
| `511260` | 74.95% | 75.66% | 85.07% | 63.44% | 64.61% | 75.68% |
| 商品袖子 | N/A | N/A | N/A | 15.86% | 14.96% | 31.28% |
| `510300` | 10.99% | 11.04% | 16.80% | 8.97% | 8.93% | 14.05% |
| `518880` | 14.06% | 12.36% | 21.75% | 11.73% | 11.57% | 17.85% |

集中度检查：

- Baseline 中 `511260` 权重大于 70% 的交易日占 86.48%。
- `agri_energy` 中 `511260` 权重大于 70% 的交易日占 13.32%，大于 60% 的交易日占 71.95%。
- `agri_energy` 的商品袖子权重大于 20% 的交易日占 19.72%，大于 25% 的交易日占 4.00%，大于 30% 的交易日占 1.60%。
- 单只商品 ETF 没有超过 20%；`159985` 最大 16.31%，`159981` 最大 15.42%。

判断：`511260` 仍是风险平价组合的主权重来源，但 `agri_energy` 相比 baseline 已经明显降低国债集中度。这个集中度在当前逆波动框架下可接受，不构成本轮淘汰理由。真正需要监控的是商品袖子在少数阶段抬升到 25%-30% 以上。

## 商品袖子收益贡献

贡献估算使用前一日权重乘以资产日收益率，未把交易费用精确归因到单资产，因此只用于方向性诊断。

`agri_energy` 全期近似贡献：

| 项目 | 贡献 |
|---|---:|
| `511260` | +12.79 pct |
| 商品袖子合计 | +15.95 pct |
| `159985` | +8.05 pct |
| `159981` | +7.91 pct |
| `510300` | +3.87 pct |
| `518880` | +11.55 pct |

商品袖子年度贡献：

| 年份 | 商品袖子 | `159985` | `159981` |
|---|---:|---:|---:|
| 2020 | +6.49 pct | +4.48 pct | +2.01 pct |
| 2021 | +5.05 pct | -0.39 pct | +5.44 pct |
| 2022 | +3.74 pct | +3.52 pct | +0.23 pct |
| 2023 | +0.96 pct | +0.47 pct | +0.49 pct |
| 2024 | -2.42 pct | -1.41 pct | -1.01 pct |
| 2025 | -0.53 pct | +0.62 pct | -1.15 pct |
| 2026 | +2.66 pct | +0.76 pct | +1.90 pct |

判断：商品袖子不是只靠单一年份贡献，2020-2022 和 2026 都有正贡献；但贡献确实偏集中在样本前半段，2024-2025 为负。它改善了同起点表现，但还不能证明跨周期稳定性。

## 交易明细诊断

`agri_energy` 按资产交易：

| 资产 | 交易笔数 | trade_value |
|---|---:|---:|
| `159981` | 13 | 0.5146 |
| `159985` | 13 | 0.4354 |
| `510300` | 13 | 0.3491 |
| `511260` | 13 | 1.5802 |
| `518880` | 13 | 0.6568 |

`agri_energy` 每个资产交易笔数相同，主要是季度再平衡触发后所有资产同步调整。相比同起点 baseline 的 27 笔交易，`agri_energy` 为 65 笔，交易笔数增加主要来自资产数量从 3 只扩展到 5 只，而不是某个商品 ETF 异常高频交易。

## 约束选择

同起点诊断仍支持继续研究 `agri_energy`，但不建议直接替换默认篮子。下一轮如果做低复杂度约束，应优先选择一个商品袖子总权重上限，而不是单 ETF 权重上限。

理由：

- 单只商品 ETF 最大权重都低于 20%，单 ETF 上限在本样本中大概率不绑定，信息增量有限。
- 商品袖子合计最大 31.28%，超过 25% 的交易日占 4.00%，超过 30% 的交易日占 1.60%；总袖子上限可以针对极端阶段，而不经常干扰正常风险平价权重。
- 一个可复核的下一轮方案是只测试 `commodity_sleeve_cap=25%`，不做 20%/25%/30% 参数网格。

## 结论

本轮建议：`refine`。

`agri_energy` 的同起点表现仍成立：年化收益从 5.71% 提高到 7.40%，Sharpe 从 1.5969 提高到 1.8149，最大回撤略好于 baseline。但它的年化换手从 0.3936 提高到 0.5820，交易笔数从 27 提高到 65，且商品袖子收益贡献有样本前半段偏集中的问题。

下一轮只建议做一个 additive 约束实验：`agri_energy` + 商品袖子总权重上限 25%。不要扩展 universe，不做参数搜索，不改变 baseline。
