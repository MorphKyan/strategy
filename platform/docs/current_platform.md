# Platform 当前有效说明

## 系统边界

`platform/` 是独立的日频事件驱动回测与模拟组合平台，不依赖 `etf_selection/` 的内部实现，也不迁移旧 `research/` 策略插件接口。

- 平台源码：`platform/src/platform_core/`
- 平台配置：`platform/configs/`
- 平台原始结果：`platform/results/`
- 平台标准报告：`platform/reports/`
- 平台数据与元数据：`platform/data/`
- 策略接口：`Strategy.generate_targets(context)`

平台可以执行由 `etf_selection/` 生成的平台配置，但 ETF 筛选和篮子构建逻辑不进入 `platform/src/platform_core/`。

## 当前架构决策

1. 平台回测使用日频事件驱动引擎，入口是 `platform/scripts/run_platform_backtest.py`。
2. 策略只返回目标权重；订单生成、费用、lot size、涨跌停、停牌、未成交重试和交易记录由执行层负责。
3. 回测估值和交易执行使用无复权原始价格；策略信号可以读取平滑后的 `adj_close`。
4. 企业行为在平台内显式建模：份额拆分在 `split_date`（基准日）之后该资产**首个真实行情日**生效（数据源价格届时才除权，基准日常停牌或价格未除权；共享逻辑在 `corporate_actions.py`，背景见 `reports/split_effective_date_fix_report.md`）；现金分红在 `ex_date` 记入 `dividend_receivables`，在 `payment_date` 转入现金。
5. checkpoint 保存完整组合状态，包括现金、持仓、成本、待执行意图、冷却池、策略状态、最后处理日期和应收分红。
6. 旧 `run_strategy(df, config)` 接口不迁移；平台策略必须实现 `Strategy.generate_targets(context)`。

## 已实现能力

- 单账户、多资产日频回测引擎。
- 从 YAML 配置加载资产、组合、单一策略、执行参数和数据路径。
- 每个 YAML 配置只定义一个策略和一个组合；回测样本窗口由运行时参数提供。
- `PortfolioState`、`Position`、`Order`、`Trade`、`PendingIntent`、`TargetPortfolio` 等核心模型。
- 现金、持仓、市值、成本、净值、待执行意图、冷却池和应收分红状态。
- 原始价格执行，`adj_close` 信号历史，涨停/跌停/停牌检查，lot size 约束，费用和滑点。
- 未成交处理：`retry_next_day`、`cancel`、`mark_failed`。
- 每日 checkpoint 与从 checkpoint 派生模拟组合。
- SQLite 元数据：实际执行的策略版本、回测记录、checkpoint 索引、模拟组合和引用关系。
- 策略版本按当前类、父类源码与参数登记，并保护已有引用；配置中的旧 `strategy_version_id` 不用于加载历史代码或替代本次身份。
- 标准实验入口、候选/基线对比、`metrics.json`、中文实验报告和可选图表。
- 研究指标：年化收益、年化波动、最大回撤、Sharpe、年化换手、交易数、订单数、拒单数、待执行意图压力和现金拖累。
- 引擎及文件重算共用周期指标函数。复合年化以净值之间的收益区间数计算；投资期保留建仓前一日基准并包含建仓成本。仅一条净值时年化收益为未知。该校正影响新计算的指标，历史报告未重写。
- 起始日期敏感性分析入口。
- HFQ 数据链校验入口。
- 平台市场数据同步入口。行情快照随 git 版本管理，同步采用**稳定写盘**：未变行保留原 `updated_at`、volume/amount 在 1% 容差内视为主备源噪音不算变化、保留文件原有行尾、内容一致时不写盘——`git diff` 只反映真实数据变化（共享函数 `data_store.write_csv_stable`，合成 3X 生成器同用）。**注意：只应在收盘后同步/提交快照**——盘中同步会把半日 K 线写进快照（曾发生），晚间同步会以小 diff 形式自动修正。
- 分红/拆分事件表是**只增不删的账本**（`corporate_actions.merge_event_table`）：上游返回缺失或键冲突时保留本地已验证事件并打警告；新拆分事件必须先通过价格交叉验证（拆后首日价 ≈ 拆前价 ÷ 比例，±15%）才会入表——曾拦下上游把 510500 两条已验证拆分替换成错误 1:0.01 的事故。
- 实盘镜像组合闭环（`platform/src/platform_core/live.py` + `notify.py` + `scripts/run_live_cycle.py`）：`reconcile` 导入真实持仓+现金覆盖组合状态并记录真实净值（mark-to-real，误差每日清零不累积）；`plan` 用真实权重+最新数据算目标，对执行引擎做 dry-run（整手取整/现金上限/费用与回测同口径）产出人可照做的"明日下单票"（`tickets/ticket_<date>.csv/.txt`），绝不模拟成交；`cycle` 一键编排 sync→reconcile→plan→每日估值→notify（非交易日自动跳过），推送支持 Server酱/SMTP（环境变量 `RQ_SERVERCHAN_KEY` 或 `RQ_SMTP_*` 零配置启用，失败不中断主流程）。每个交易日按收盘价对真实持仓 mark-to-market 并追加进 `real_nav.csv`（真实净值日频序列，供月度归因与组合列表页使用）；推送分两条——markdown 组合日报（总值/日变动/现金/各资产权重/阈值带状态）交易日必发，触发调仓时下单票作为独立第二条。产物在 `results/live_portfolios/<id>/`。`cycle --shadow <sim_id>` 可让影子模拟组合每交易日增量跟跑（`SimPortfolio.load()` 从持久化状态恢复）。
- 实盘月度归因（`platform/src/platform_core/attribution.py` + `scripts/report_live_attribution.py`）：对齐真实 `real_nav.csv` 与影子组合净值，输出区间收益差、年化 tracking error 与粗拆（现金拖累差 + 执行/结构残差），**只记录不改持仓**；收益观测不足 5 个判"样本不足仅存档"。报告写入 `reports/live/`（含真实账户金额，已 gitignore 不入库）。
- 实盘策略运行状态保存在 `portfolio_state.json` 的 `strategy_state._live_strategy_runtime`，每天重启与持仓对账后继续恢复；旧账户没有快照时，已有真实持仓视为已完成首次建仓。同日重跑从当日计算前的状态重放；策略名称或参数变化时重新初始化运行状态。
- 回测 checkpoint 与模拟组合通过 `strategy_state._strategy_runtime` 保存策略身份和运行状态，模拟重启后继续恢复；宏观因子策略的平滑系数矩阵也纳入该状态。模拟和实盘共用日历边界补齐，避免每日增量运行被误判为月末。历史出票不得回退较新的账户或运行状态；同日改为无操作时移除原订单 CSV。
- 模拟推进在状态副本中计算，运行文件完成且最新状态原子保存成功后才更新内存；失败后可在原实例重试。新运行的 manifest 标记 `requires_state_commit`，状态文件的 `committed_run_ids` 记录已提交运行，归因跳过未提交的候选产物。补齐的日历边界仅供信号判断，不作为可成交日期。新组合保留原始 checkpoint 来源，恢复不会把它改成当前状态文件。
- 下单票统一使用最新 `close` 估算股数并保留配置的费用、滑点；回测与模拟的成交价格仍取 `execution.execution_price_field`（默认 `open`）。三者通过 `ExecutionConfig.from_config()` 共用执行配置构造，包括参与率冲击和分资产容差。
- 实盘对账、出票、估值及同步后的环路均检查所有配置标的在截至日的最新行情日期。日期不一致或任一标的没有有效行情时，在写入账户、净值或票据前报错；有明确当日行情行的停牌标的保留原有拒单处理。原有 7 天新鲜度检查继续生效。
- 本地只读 Streamlit 看板（`platform/src/platform_dashboard/`）：概览、回测分析（净值/收益率双模式 + 近N月区间归零、基准对比与超额曲线、月度收益热力图、年度收益、日收益分布、滚动波动/Sharpe、训练 vs 冻结样本对照、含现金层的持仓面积图、订单与交易表）、回测对比（2–5 个回测在所选区间首日对齐归一 + 指标对照表）、策略配置浏览。

## 内置策略范围

当前 `BUILTIN_STRATEGIES` 中保留的策略包括：

- `monthly_equal_weight`
- `risk_parity`
- `risk_parity_ewma`
- `risk_parity_ewma_dd_recovery`
- `risk_parity_lw_cov`
- `hrp`
- `risk_parity_cvar_dynamic_budget`
- `adaptive_risk_deviation_volatility_triggered`
- `cluster_representative_damped_risk_parity`
- `risk_parity_gerber`
- `risk_parity_ewma_cov`
- `fixed_weight_threshold`（R038，永久组合式固定权重 + 5/25 阈值带；扩展策略按蓝图 C1 放在 `platform/src/platform_core/strategies/` 包内）

失败或 research-only 策略不应继续注册在 `BUILTIN_STRATEGIES` 中。

## 基本面 PIT 视图入口

`scripts/sync_pit_fundamental_views.py` 按 `--symbols` 选择要更新的标的；`--data-dir` 默认指向 `platform/data/`，`--output` 可指定输出文件。只使用本次选择需要的输入，全部生成成功后才写盘；原输出中未选择的标的保留。运行前检查所选行情的新鲜度与对齐。

输入文件位于 `data/fundamental_macro/`，日期使用 `YYYY-MM-DD`：

| 输入 | 必需字段与用途 |
| --- | --- |
| `china_bond_yields_daily_pit.csv` | `date,bond_ytm_30y,bond_ytm_10y`；收益率以百分数表示，可提供 `available_date`。缺少披露日期时，保守地从下一条国债报价日起使用。 |
| `china_cpi_releases.csv` | `available_date,cpi_yoy_pct`；黄金实际收益率所需的真实 CPI 发布日期和值。 |
| `index_dividend_yield_releases.csv` | `symbol,available_date,dividend_yield_pct`；指数自身披露的股息率，`symbol` 保留前导零。 |
| `futures_contract_expiries.csv` | `contract,expiry_date`；例如 `M2405`，到期日必须来自实际合约规则，随后抓取对应结算价与持仓量。 |

带 `available_date` 的输入可另含 `observation_date`，用于检查披露日期没有早于观测日期。`available_date` 表示允许进入本平台决策输入的首日；仅在收盘后可得的数据应填后续交易日。首次可用日前保持缺失，不用零补齐。

ETF 股息率使用 `data/platform_dividends.csv` 中同一 ETF 的每份分红及原始收盘价，并按 `platform_splits.csv` 调整分红单位；不把 ETF 分红除以指数点位，也不借用其他 ETF。期货价差采用实际到期日，结算数据从下一交易日起进入视图；任何必需合约抓取失败都会终止。

缺少真实披露日期、指数股息率或合约到期日文件时，补齐可核验来源后再运行；脚本不再生成假定发布日期和固定收益率。既有 PIT CSV 和历史绩效未自动重建，也没有因本次代码修复而获得重新认证。

`risk_parity_black_litterman` 的现有计算是基本面按 ES 缩放预算后的协方差风险平价，没有贝叶斯后验；`risk_parity_macro_factor` 是带资产预算软惩罚的 PCA 协方差因子分配。沿用注册名以加载现有配置，不把这两项标为精确论文复现。约束 ES 保留单一 SLSQP 预算误差求解，删除了未被固定配置使用的 `bisection` 选择及静默回退；求解失败时停止。

`scripts/fetch_etf_nav.py` 要求分页总数稳定、完整且日期唯一，单位/累计净值均为有限正数；刷新不得丢失任何已存日期。`--config` 只选择 ETF，`--report` 先检查行情再通过 `EtfPremiumStore` 扣除发布滞后，输出可观测溢价及对应观测日，不展示尚不可用的同日净值比值。

回测、模拟及实盘的企业行为默认与行情共用 `data.market_store_dir` 或 `data.data_dir`，未配置目录时才使用 `platform/data/`。可用 `data.dividends_csv`、`data.splits_csv` 显式指定文件；实盘原有 `live.dividends_path` 优先。显式文件缺失会报错，避免将配置错误当作没有事件。回测与模拟共用事件加载器，拒绝重复日期/代码、无效日期、付款早于除息、负或非有限股息及非正拆分比例。

## ES 稳健性诊断工具

`scripts/analyze_es_robustness.py` 复用平台行情与复权入口，分别读取两份配置的数据目录，并检查新鲜度与跨代理末日对齐。它输出纯权重/风险预算诊断；交易成本和执行结果仍由实际回测提供。配置矩阵使用本次的置信水平，写入 `--generated-config-dir/<timestamp>/`；诊断输出和配置都不允许覆盖旧产物。

`scripts/summarize_es_robustness.py` 从 `metrics.json` 或回测 manifest 的已保存 `metrics` 读取绩效，无交易的运行输出空执行诊断。敏感性默认保留全部满足观测数的起点，`--start-date` 可显式筛选；`--diagnostics-csv` 显式提供权重比较输入，不从输出目录父级猜文件。输出目录必须新建。

汇总表的 `theoretical_*` 是以当前行情和当前无约束 ES 代码重算的参考值，另有 `theoretical_basis` 标明来源；它不代表历史策略当时的完整目标，也不替代已保存的执行指标。对移动后的敏感性目录，优先读取与 manifest 同目录的 `sensitivity_summary.csv`。

## 常用入口

从仓库根目录运行：

```powershell
.\env\Scripts\python.exe platform\scripts\run_platform_backtest.py --config configs\domestic_rolling_bond_10y.yaml --start-date 2019-02-28 --end-date 2025-06-30
.\env\Scripts\python.exe platform\scripts\run_platform_experiment.py --config configs\domestic_rolling_bond_10y.yaml --start-date 2019-02-28 --end-date 2025-06-30
.\env\Scripts\python.exe platform\scripts\run_sensitivity.py --config configs\domestic_rolling_bond_10y.yaml --end-date 2025-06-30
.\env\Scripts\python.exe platform\scripts\sync_platform_data.py --config configs\domestic_rolling_bond_10y.yaml
.\env\Scripts\python.exe platform\scripts\sync_all_market_data.py
.\env\Scripts\python.exe platform\scripts\get_common_date_range.py --config platform\configs\domestic_rolling_bond_10y.yaml
.\env\Scripts\python.exe platform\scripts\run_sim_portfolio.py --config configs\domestic_rolling_bond_10y.yaml --checkpoint <checkpoint.json> --asof-date <YYYY-MM-DD>
.\env\Scripts\python.exe platform\scripts\run_dashboard.py
.\env\Scripts\python.exe platform\scripts\run_live_cycle.py reconcile --config configs\domestic_rolling_bond_10y.yaml --holdings <holdings.csv> --cash <float> [--asof-date YYYY-MM-DD]
.\env\Scripts\python.exe platform\scripts\run_live_cycle.py plan --config configs\domestic_rolling_bond_10y.yaml [--asof-date YYYY-MM-DD] [--notify]
.\env\Scripts\python.exe platform\scripts\run_live_cycle.py cycle --config configs\domestic_rolling_bond_10y.yaml [--sync] [--notify] [--holdings <csv> --cash <float>] [--force] [--shadow <sim_id>]
.\env\Scripts\python.exe platform\scripts\report_live_attribution.py --live-id <live_id> --shadow-id <sim_id> [--month YYYY-MM] [--notify]
```

上述命令默认使用 venv/uv 布局的 `.\env\Scripts\python.exe`；如果本地环境使用 conda/root 布局，可等价替换为 `.\env\python.exe`。

看板默认端口 8501，可用 `PORT` 环境变量覆盖。实盘 `run_live_cycle.py` 的持仓文件表头为 `code,quantity[,cost_basis]`；`reconcile`/`plan` 单独使用时先同步行情（否则被 7 天数据新鲜度闸门拦下），`cycle --sync` 会自动同步；每个工作日收盘后定时跑 `cycle --sync --notify` 的任务计划注册命令见脚本 docstring。

当前定时任务配置 `configs/capital_100k/es_252d_fhs_stepdown_trend_200k_v2_563020_511130.yaml` 使用 `rebalance_frequency: daily`：每个交易日重算 FHS-ES、波动率控制及趋势过滤后的目标，保留 5 个百分点的调仓偏差阈值。每日 TXT 票据和日报列出全部资产与现金的当前/目标权重、差额；未触发阈值时仍保留目标监控，订单 CSV 仅在生成调仓目标时写出。上次调仓时间只取截至目标计算日 `execution_ledger.csv` 中正数量 BUY/SELL 的最近日期，排除分红、划拨、零数量及未来记录；没有流水时显示未知，不用出票日或对账日代替。票据不代表真实成交，持仓仍以人工对账为准。

平台脚本会把工作目录切到 `platform/`，因此脚本参数中的 `configs/`、`data/`、`results/` 等相对路径均按平台目录解析。

## 研究验收规则

- 用户定向研究使用用户指定的窗口，默认运行 `default + stress`；`dynamic_participation` 由用户或流动性研究需要决定。
- 起点敏感性默认每两个自然月生成一个 `start_date`，候选与基线使用相同窗口。诊断交易日步长需显式指定 `--step`。
- 自主选题、固定样本划分、候选冻结及独立验收遵循根目录 `.agents/skills/run-autonomous-quant-research/SKILL.md`，不扩展到所有历史分析任务。
- 标准实验报告提供指标对比及验证范围，取消无调用方且对定向研究强加阈值的自动“接受/继续改进”判断。
- 报告必须读取实际 artifact，优先读取 `metrics.json`，不能凭记忆推断指标。
- 如果存在回测 artifact，报告必须包含换手率、交易数、订单数和拒单数。
- 新生成的 markdown 报告和总结必须使用中文；代码标识符、文件名、metric key 和命令保持原文。

## Artifact 位置

- 固定配置完整共同历史的直接回测：`platform/results/backtests/<run_id>/`
- 截短区间、生成配置或来源无法证明的直接回测：`platform/results/temporary_backtests/direct/<run_id>/`
- 标准实验原始结果：`platform/results/temporary_backtests/experiments/<experiment>/<timestamp>/<strategy>/<run_id>/`
- manifest 的 `artifact_provenance` 记录配置来源及实际/共同区间；无来源证明的旧产物仅在看板启用临时回测选项后显示，历史文件不改写。
- 标准实验报告：`platform/reports/experiments/<experiment>/<timestamp>/`
- 敏感性原始结果：`platform/results/sensitivity_raw/<strategy>/<timestamp>/`
- 敏感性报告：`platform/reports/sensitivity/<strategy>/<timestamp>/`
- 数据校验报告：`platform/reports/data_validation/<timestamp>/`

原始结果目录保存执行级 artifact；报告目录保存决策级摘要、指标、配置副本和原始路径引用。
