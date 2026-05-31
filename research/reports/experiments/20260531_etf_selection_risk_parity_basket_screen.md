# ETF Selection 风险平价篮子筛选实验报告

## 目标

基于 `etf_selection/config/etf_universe.yaml` 当前 ETF universe 做一轮风险平价篮子筛选，只保留 2-3 个结构差异明显的候选组合，不做参数搜索，并用 research 标准实验与 `configs/risk_parity.yaml` 比较。

## 假设

在默认风险平价逻辑、交易成本和季度再平衡规则不变的前提下，引入当前 universe 中的单商品 ETF 袖子，可能改善组合分散度和风险调整后收益；但如果商品袖子带来更高相关性、回撤或换手，则应优先淘汰。

## 本轮输入与来源

- ETF universe：`etf_selection/config/etf_universe.yaml`
- ETF selection 筛选输出：`etf_selection/reports/20260531_010055/`
- Research baseline config：`research/configs/risk_parity.yaml`
- Research 标准实验脚本：`research/scripts/run_experiment.py`
- 外部文献：本轮未使用，也不提出新的文献支持策略方向；本轮结论只基于当前 universe 的数据筛选和标准回测产物。

## 筛选过程

先运行 ETF selection 袖子筛选：

```powershell
.\env\python.exe etf_selection\scripts\screen_etf_sleeves.py --config etf_selection\config\etf_universe.yaml
```

当前 universe 中合格袖子如下：

- `gold`：`518880` 黄金ETF，历史 12.35 年。
- `hs300`：`510300` 沪深300ETF、`510310` 沪深300ETF易方达；二者是高度相近的同类替代，本轮优先保留流动性和得分更高的 `510300`。
- `bond`：`511260` 十年国债ETF；`511130` 30年国债ETF历史仅 1.88 年，被硬过滤。
- `commodity`：`159980` 有色期货ETF、`159985` 豆粕ETF、`159981` 能源化工ETF；当前 universe 没有 broad commodity ETF，因此按规则允许使用多个单商品 ETF。

ETF selection 生成 8 个完整篮子。本轮排除仅替换 `510300`/`510310` 的近似重复，只保留 3 个商品袖子结构不同的候选。

## 保留候选

| 候选 | 资产覆盖 | ETF selection 共同历史 | 平均绝对相关性 | 最大绝对相关性 | 逆波动 HHI | 逆波动权重集中点 |
|---|---|---:|---:|---:|---:|---|
| `agri_energy` | 黄金、沪深300、豆粕、能源化工、十年国债 | 2022-04-13 至 2026-05-19，3.94 年 | 0.1249 | 0.3180 | 0.4856 | `511260` 67.76% |
| `all_commodities` | 黄金、沪深300、有色、豆粕、能源化工、十年国债 | 2022-04-13 至 2026-05-19，3.94 年 | 0.1886 | 0.4380 | 0.4196 | `511260` 62.54% |
| `metals_agri` | 黄金、沪深300、有色、豆粕、十年国债 | 2022-04-13 至 2026-05-19，3.94 年 | 0.1844 | 0.4380 | 0.4709 | `511260` 66.54% |

解释：

- `agri_energy` 是本轮最高分候选，跨资产平均绝对相关性最低，结构上覆盖农业和能化商品。
- `all_commodities` 覆盖全部三只合格单商品 ETF，逆波动 HHI 最低，但相关性和回撤风险更高。
- `metals_agri` 用有色替代能化，保留一个偏周期金属商品暴露，作为 `agri_energy` 的结构对照。

## 新增配置与数据

新增 research 候选配置：

- `research/configs/generated/risk_parity_etfsel_agri_energy_20260531.yaml`
- `research/configs/generated/risk_parity_etfsel_all_commodities_20260531.yaml`
- `research/configs/generated/risk_parity_etfsel_metals_agri_20260531.yaml`

为 research 标准实验补齐本地后复权数据：

- `research/data/159980.csv`
- `research/data/159980_hfq_factor.csv`
- `research/data/159981.csv`
- `research/data/159981_hfq_factor.csv`
- `research/data/159985.csv`
- `research/data/159985_hfq_factor.csv`

数据通过 research `DataHandler.fetch_codes_data()` 获取，未复用 platform 数据文件。

## Research 标准实验命令

```powershell
.\env\python.exe research\scripts\run_experiment.py --strategy risk_parity --config configs/generated/risk_parity_etfsel_agri_energy_20260531.yaml --baseline-config configs/risk_parity.yaml
.\env\python.exe research\scripts\run_experiment.py --strategy risk_parity --config configs/generated/risk_parity_etfsel_all_commodities_20260531.yaml --baseline-config configs/risk_parity.yaml
.\env\python.exe research\scripts\run_experiment.py --strategy risk_parity --config configs/generated/risk_parity_etfsel_metals_agri_20260531.yaml --baseline-config configs/risk_parity.yaml
```

标准实验报告目录：

- `research/reports/experiments/risk_parity/20260531_010425/`
- `research/reports/experiments/risk_parity/20260531_010439/`
- `research/reports/experiments/risk_parity/20260531_010451/`

候选 raw artifacts：

- `research/results/risk_parity/20260531_010426/`
- `research/results/risk_parity/20260531_010440/`
- `research/results/risk_parity/20260531_010452/`

## metrics.json 对比

指标均读取自对应 `metrics.json`。仓库当前没有样本外指标，`oos_metrics_available=false`。

| 指标 | Baseline `configs/risk_parity.yaml` | `agri_energy` | `all_commodities` | `metals_agri` |
|---|---:|---:|---:|---:|
| 回测起止 | 2017-08-24 至 2026-05-19 | 2020-01-17 至 2026-05-19 | 2020-01-17 至 2026-05-19 | 2020-01-02 至 2026-05-19 |
| observations | 2115 | 1531 | 1531 | 1542 |
| total_return | 62.39% | 54.23% | 62.72% | 57.18% |
| annualized_return | 5.95% | 7.40% | 8.35% | 7.68% |
| annualized_volatility | 3.53% | 4.08% | 4.73% | 4.27% |
| max_drawdown | -4.41% | -4.01% | -5.34% | -4.40% |
| sharpe_ratio | 1.6851 | 1.8149 | 1.7637 | 1.7989 |
| annualized_turnover | 0.4657 | 0.5820 | 0.6493 | 0.5836 |
| trade_count | 48 | 65 | 78 | 65 |

相对 baseline 的关键差值：

| 候选 | 年化收益差 | 年化波动差 | 最大回撤差 | Sharpe 差 | 年化换手差 | 交易笔数差 |
|---|---:|---:|---:|---:|---:|---:|
| `agri_energy` | +1.45 pct | +0.55 pct | +0.39 pct | +0.1297 | +0.1163 | +17 |
| `all_commodities` | +2.40 pct | +1.20 pct | -0.94 pct | +0.0786 | +0.1836 | +30 |
| `metals_agri` | +1.73 pct | +0.74 pct | +0.00 pct | +0.1138 | +0.1178 | +17 |

注意：候选组合因商品 ETF 共同历史较短，标准实验中的候选回测期短于 baseline。以上为按仓库现有 `run_experiment.py` 生成的标准产物对比，不应解读为严格同起点样本比较。

## 结论

本轮建议 `refine`，不直接替换默认篮子。

- 优先保留 `agri_energy` 进入下一轮。它的 ETF selection 平均绝对相关性最低，research 标准实验中 Sharpe 最高，最大回撤也未恶化；主要代价是年化换手从 0.4657 升至 0.5820，交易笔数从 48 增至 65。
- 暂不推进 `all_commodities`。它年化收益最高且 HHI 最低，但最大回撤恶化到 -5.34%，年化换手升至 0.6493，交易笔数升至 78，新增复杂度和执行成本没有足够补偿。
- 暂不推进 `metals_agri`。它的 Sharpe 改善接近 `agri_energy`，但相关性和 HHI 均不如 `agri_energy`，且换手代价相近。

## 下一轮 refine 建议

1. 只围绕 `agri_energy` 做下一轮，不扩展 universe，不做参数搜索。
2. 做一次同起点诊断：用 2020-01-17 至 2026-05-19 对 baseline 和 `agri_energy` 切片比较，避免当前标准实验候选和 baseline 起点不同造成解释偏差。
3. 检查 `agri_energy` 的权重路径和交易明细，重点确认 `511260` 逆波动权重长期集中是否可接受，以及商品袖子是否只是短样本收益贡献。
4. 如果同起点诊断仍成立，再考虑一个低复杂度约束：商品袖子总权重或单 ETF 权重上限。该步骤应作为新的 additive variant 或 config 实验单独记录，不在本轮结果中混入。
