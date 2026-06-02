# 无债券 ETF 风险平价篮子实验汇总

## 假设
在不引入债券、国债、政金债、信用债、可转债或现金类 ETF 的前提下，使用黄金和商品袖替代债券防御袖，可能提高收益弹性，但需要验证其回撤、波动和换手是否仍可接受。

## 数据与筛选边界
- 来源 universe：`etf_selection/config/etf_universe.yaml`。
- 排除：`bond` sleeve，以及名称/子类含债券、国债、政金债、信用债、可转债、现金、货币的 ETF。
- 当前 universe 剔除债券后只有 `510300`、`510310`、`518880`、`159980`、`159981`、`159985`；没有红利、低波或跨市场权益 ETF，所以本轮没有擅自扩大覆盖。
- `research/data` 原本缺少 3 个商品 ETF。因当前 Python 环境无 `finshare`，已把 `platform/data` 中现有本地文件转换为 research 需要的 `close_price` 与 `hfq_factor` schema；价格调整来源是原文件 `adjust_factor`，未改 common-history 处理。
- 样本外指标：`metrics.json` 中 `oos_metrics_available=false`，仓库本轮未生成样本外指标。

## 文献来源
- Gorton and Rouwenhorst, `Facts and Fantasies about Commodity Futures`, NBER Working Paper 10595，说明商品期货与股票/债券的周期暴露不同，并与通胀相关。
- Baur and Lucey, `Is Gold a Hedge or a Safe Haven?`, Financial Review，说明黄金对权益极端情形有短期避险属性，但该属性不是长期稳定替代。
- Lohre, Opfer and Orszag, `Diversifying Risk Parity`，说明风险平价仍应关注风险源分散，而不是仅增加资产数量。
- 文献记录：`research/reports/literature/20260531_010444_no_bond_basket_sources.md`。

## 候选筛选指标
| 候选 | 资产覆盖 | 共同历史 | avg_abs_corr | max_abs_corr | inverse_vol_hhi | 回撤控制说明 |
|---|---|---:|---:|---:|---:|---|
| 无债券-农业能源商品篮子 | `510300, 518880, 159985, 159981` | 3.94 年 | 0.1231 | 0.2303 | 0.2549 | 不使用债券代理；依赖黄金/商品低相关、季度再平衡、`rebalance_threshold` 与倒数波动率权重。权益和商品同步下跌时，预期回撤会显著高于默认含国债篮子。 |
| 无债券-三商品分散篮子 | `510300, 518880, 159980, 159985, 159981` | 3.94 年 | 0.2151 | 0.4380 | 0.2031 | 不使用债券代理；依赖黄金/商品低相关、季度再平衡、`rebalance_threshold` 与倒数波动率权重。权益和商品同步下跌时，预期回撤会显著高于默认含国债篮子。 |
| 无债券-周期商品篮子 | `510300, 518880, 159980, 159981` | 3.94 年 | 0.2742 | 0.4380 | 0.2547 | 不使用债券代理；依赖黄金/商品低相关、季度再平衡、`rebalance_threshold` 与倒数波动率权重。权益和商品同步下跌时，预期回撤会显著高于默认含国债篮子。 |

## 标准实验命令
- 无债券-农业能源商品篮子：`python research\scripts\run_experiment.py --strategy risk_parity --config configs/generated/risk_parity_no_bond_agri_energy.yaml --baseline-config configs/risk_parity.yaml`
- 无债券-三商品分散篮子：`python research\scripts\run_experiment.py --strategy risk_parity --config configs/generated/risk_parity_no_bond_full_commodity.yaml --baseline-config configs/risk_parity.yaml`
- 无债券-周期商品篮子：`python research\scripts\run_experiment.py --strategy risk_parity --config configs/generated/risk_parity_no_bond_cyclical_commodity.yaml --baseline-config configs/risk_parity.yaml`

## `metrics.json` 指标对比
Baseline 默认篮子：`510300, 518880, 511260`；窗口 2017-08-24 至 2026-05-19；年化收益 5.95%，波动 3.53%，最大回撤 -4.41%，Sharpe 1.6851，Calmar 1.3502，annualized_turnover 0.4657，turnover_total 3.9090，trade_count 48。

| 候选 | 窗口 | 年化收益 | 波动率 | 最大回撤 | Sharpe | Calmar | annualized_turnover | turnover_total | trade_count | 建议 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 无债券-农业能源商品篮子 | 2022-04-13 至 2026-05-19 | 12.08% | 9.95% | -11.82% | 1.2140 | 1.0216 | 0.9222 | 3.6303 | 48 | refine |
| 无债券-三商品分散篮子 | 2022-04-13 至 2026-05-19 | 11.45% | 10.36% | -12.60% | 1.1052 | 0.9084 | 0.9020 | 3.5506 | 60 | reject |
| 无债券-周期商品篮子 | 2022-04-13 至 2026-05-19 | 12.37% | 11.41% | -12.33% | 1.0840 | 1.0031 | 1.0068 | 3.9632 | 56 | reject |

## 结论
- `accept / reject / refine`：整体为 `refine`，不接受作为默认含国债篮子的替代。
- 最值得保留的候选是 `无债券-农业能源商品篮子`：它在无债券候选中相关性最低、Sharpe 最高，但最大回撤 `-11.82%` 明显劣于默认篮子 `-4.41%`，Sharpe 和 Calmar 也低于默认。
- `无债券-三商品分散篮子` 虽然 HHI 最低，但商品内部相关性更高，回撤和换手没有补偿风险。
- `无债券-周期商品篮子` 年化收益最高，但波动、回撤和换手最高，风险调整后表现不足。
- 由于候选窗口从 `2022-04-13` 开始，而默认篮子从 `2017-08-24` 开始，跨窗口比较不应解读为严格同样本胜负；但即使用年化指标看，无债券候选也没有改善 Sharpe、Calmar 或回撤。

## 文件变更
- 新增 research 配置：`research/configs/generated/risk_parity_no_bond_agri_energy.yaml`、`research/configs/generated/risk_parity_no_bond_full_commodity.yaml`、`research/configs/generated/risk_parity_no_bond_cyclical_commodity.yaml`。
- 新增筛选报告：`etf_selection/reports/20260531_010444_no_bond_risk_parity_screen/`。
- 新增标准实验报告：`research/reports/experiments/risk_parity/20260531_010739/`、`20260531_010753/`、`20260531_010804/`。
- 新增汇总报告：`research/reports/experiments/no_bond_risk_parity_baskets/20260531_011000/`。
- 新增文献记录：`research/reports/literature/20260531_010444_no_bond_basket_sources.md`。
- 新增 research 商品数据 schema 转换文件：`research/data/159980*.csv`、`research/data/159981*.csv`、`research/data/159985*.csv`。

## 验证
- 已确认 3 个候选 raw artifacts 写入 `research/results/risk_parity/<timestamp>/`。
- 已确认 3 个候选标准 artifacts 写入 `research/reports/experiments/risk_parity/<timestamp>/`，并从各自 `metrics.json` 读取指标。
- 首次运行 `20260531_010507` 因缺少 `seaborn` 失败；安装 `seaborn` 后重跑成功，该失败目录保留为环境诊断记录。
