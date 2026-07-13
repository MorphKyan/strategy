# R039 行业 ETF 动量轮动（卫星仓）研究报告 —— 判定：Failed（research-only）

> 日期：2026-07-12
> 课题蓝图：`platform/docs/r039_rotation_blueprint.md`
> 研究笔记：`research-dashboard/notes/R039_industry_momentum_rotation.md`
> 结论一句话：**1M+3M 混合动量的行业 ETF 月频 Top-3 轮动在训练样本上相对行业等权基线年化落后 10.5pp，32 个起始日中仅 1 个为正，三滑点场景一致，判 Failed；策略代码保留为 research-only，撤销注册，未触碰冻结样本。**

---

## 1. 假设与设计

**假设**：A 股行业层面动量（文献支持）+ 排名缓冲带（R038 阈值带思想移植）+ 负动量持币闸门，能以月频长多 Top-3 形态获得相对"持有全部行业等权"的超额收益，作为核心仓（R038）之外的高波卫星仓。

**候选**：`industry_momentum_rotation`（`platform/src/platform_core/strategies/rotation.py`）
参数全部先验冻结、零搜索（蓝图 §2.3）：momentum_windows=[21,63]（等权混合）、skip_days=5、top_n=3、rank_buffer=2、abs_momentum_floor=0.0、rebalance_threshold=0.05、月频。

**基线**：`domestic_industry_equal_weight.yaml`——同一行业池 16 只 ETF 月度等权（该配置按 Hard Rule 8 保留，供轮动线后续候选复用）。

**行业池**（16 只，准入标准：首日 ≤ 2020-03-31、行业互斥、股票型行业/主题 ETF）：
512880 证券 / 512800 银行 / 512010 医药 / 159928 消费 / 512690 酒 / 512660 军工 / 512400 有色 / 512980 传媒 / 515000 科技 / 512480 半导体 / 515050 5G通信 / 512200 地产 / 515220 煤炭 / 515700 新能车 / 515210 钢铁 / 159996 家电。共同起始日 2020-03-16（159996 上市）。

## 2. 数据与命令（可复现）

- 行情：16 只新 ETF 全量不复权日线来自 sina（akshare `fund_etf_hist_sina`，2026-07-12 抓取入库 `platform/data/<code>.csv`）；后复权因子 sidecar 由分红/拆分事件构造（除息日 `prev/(prev-div)`、拆分生效日 ×ratio，与 `corporate_actions.py` 生效日口径一致），事件表 `platform_dividends.csv`/`platform_splits.csv` 已扩容至 28 只（akshare `fund_open_fund_info_em`）。所有事件均与原始价格跳变逐一核对（如酒 ETF 2021-12-31 除息 −27.1% ↔ 每份分红 0.35 元）。
- 主源防护：`MarketDataStore.sync_assets` 新增历史收缩保护（`_guard_history_shrink`），防止 eastmoney 限流时降级源短窗数据覆盖长历史（本次实测 baostock 的 ETF 数据仅从 2026-01 起）。
- 命令（训练样本，`cwd` 任意，脚本自切到 platform/）：

```powershell
.\env\Scripts\python.exe platform\scripts\run_platform_experiment.py --config configs\r9_rotation_industry_momentum.yaml --baseline-config configs\domestic_industry_equal_weight.yaml --experiment-name r039_industry_rotation --start-date 2020-03-16 --end-date 2025-06-30 --slippage-scenario all
.\env\Scripts\python.exe platform\scripts\run_sensitivity.py --config configs\r9_rotation_industry_momentum.yaml --calendar-month-step 2 --end-date 2025-06-30
.\env\Scripts\python.exe platform\scripts\run_sensitivity.py --config configs\domestic_industry_equal_weight.yaml --calendar-month-step 2 --end-date 2025-06-30
```

（候选配置 `r9_rotation_industry_momentum.yaml` 判 Failed 后已删除；其完整副本存于实验报告目录 `reports/experiments/r039_industry_rotation_default/20260712_031354/candidate_config.yaml`。）

## 3. 训练样本结果（2020-03-16 ~ 2025-06-30）

| 指标（default 场景） | 候选（轮动） | 基线（行业等权） |
|---|---|---|
| 总收益 | **−17.46%** | **+39.71%** |
| 年化收益 | −3.70% | +6.79% |
| 年化波动 | 23.7% | 20.4% |
| Sharpe | −0.16 | 0.33 |
| 最大回撤 | −53.3% | −36.3% |
| 年化双边换手（金额） | 4.48× | 0.34× |
| 交易 / 订单 / 拒单 | 209 / 210 / 1 | 886 / 891 / 5 |
| 平均现金权重 | 14.6% | 0.1% |
| 年化费用拖累 | 0.18% | 0.07% |

三滑点场景结论一致：stress 下候选年化 −4.43% vs 基线 +6.72%；dynamic_participation 下 −3.69% vs +6.79%。**费用与滑点不是败因（合计不足 0.5pp/年），信号本身是败因。**

分年对比（default）：

| 年份 | 候选 | 基线 | 差 |
|---|---|---|---|
| 2020（3-16 起） | +43.3% | +44.0% | ≈0 |
| 2021 | −5.8% | +12.3% | −18.1pp |
| 2022 | −33.8% | −20.0% | −13.8pp |
| 2023 | +2.7% | −5.0% | +7.7pp |
| 2024 | −6.9% | +10.8% | −17.7pp |
| 2025H1 | −3.5% | +2.6% | −6.1pp |

## 4. 起始日敏感性（每 2 自然月一个起点 × 32 × 三场景）

| | 候选 | 基线 |
|---|---|---|
| 年化收益中位数 | **−8.2%** | +2.0% |
| 年化为正的起点占比 | **3%（1/32）** | 75% |
| 年化区间 | [−15.0%, +4.3%] | [−9.2%, +46.2%] |

唯一为正的起点是最早的 2020-03（吃满 2020 单边牛）。失败与起点无关，是结构性的。

## 5. 败因解剖（供后续迭代者引以为鉴）

1. **鞭打（whipsaw）**：2021–2022 A 股行业以"急涨急跌 + 快速轮动"为主，月频动量每次都在确认趋势后入场、趋势反转后离场，年化 4.5× 换手全部换在噪声上。这与 Liu-Stambaugh-Yuan (2019) "A 股各期限过去赢家倾向反转"的结论一致；文献中显著的行业动量多为**多空构造、且样本偏 2017 年以前**——长多 Top-3 形态在 2021 后的 regime 中不成立。
2. **V 型反转双重踩踏（实录）**：2024-09-30 策略因负动量闸门仅持银行 ETF（约 2/3 现金），完整踏空 9/24 起的暴涨；2024-10-08（情绪顶点日）按新动量追入家电/地产/券商，次日 −7.1%。蓝图 §2.4 预判的"固有成本"在数据里如期出现，且量级足以毁掉全年。
3. **闸门的现金拖累**：平均 14.6% 现金在震荡上行段持续漏收益；它换来的回撤保护（−53% vs 基线 −36%）反而是负的——集中持仓 3 只行业的尾部远大于闸门省下的部分。
4. 排名缓冲带方向正确但杯水车薪：它把换手从"每月全换"压到 1.7 次换仓/月，省下的费用相对信号亏损（10.5pp/年）不在一个量级。

## 6. 判定与处置

- **判定：Failed。** 未运行冻结样本（纪律：仅冻结成功候选后允许触碰）。
- 处置（Hard Rule 3 / Acceptance Guidance）：
  - `industry_momentum_rotation` 从 `BUILTIN_STRATEGIES` 撤销注册；`strategies/rotation.py` 保留为 research-only（含判定说明），pytest（10 例）保留并新增"确未注册"回归断言。
  - 候选配置删除；**基线配置 `domestic_industry_equal_weight.yaml` 保留**（Hard Rule 8，供 D2/D3 复用）。
  - 16 只行业 ETF 行情/因子/事件数据保留入库（中性基础设施，任何后续行业研究可用）。
- **对卫星仓诉求的建议**：本结果不否定"高波卫星仓"目标本身，但否定了"月频价格动量轮动"这条路。若继续，优先级重排：D2（拥挤度否决）预计只能修复 2024-10-08 型追顶（几个 pp），修不动 2021/2022 的鞭打主亏（>13pp/年），**不建议单独立项**；更值得试的方向是把"行业等权持有 + 阈值带再平衡"（即本课题基线 + R038 纪律）作为卫星仓候选——基线本身年化 6.8%、中位数起点 +2.0%，且与核心仓相关性结构不同。

## 7. 环境与工程备注

- eastmoney 主源对本机连续请求约 11 次后限流（代理与直连均被掐断），finshare 降级链 baostock/tencent 的 ETF 历史分别仅有 ~6 个月 / ~1000 交易日，**不能用于建史**；sina 路线（akshare）可拿全量。已在 `sync_all_market_data.py` 扩容资产清单，配合历史收缩保护，日常增量同步安全。
- sina 与 eastmoney 的 `volume` 单位不一致（股 vs 手）；`amount`（元）一致。平台当前只消费价格与 amount（dynamic_participation 滑点），无影响；做量能类信号时需先统一口径。
- 行情快照随 git 版本管理：本次新增 16 只 ETF 的 CSV/因子文件与扩容后的事件表待提交时一并入库（约 +3 万行 CSV），建议与仓库 owner 确认提交节奏。
