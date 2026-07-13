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
- SQLite 元数据：策略草稿、策略版本、回测记录、checkpoint 索引、模拟组合和引用关系。
- 策略版本发布和已引用版本删除保护。
- 标准实验入口、候选/基线对比、`metrics.json`、中文实验报告和可选图表。
- 研究指标：年化收益、年化波动、最大回撤、Sharpe、年化换手、交易数、订单数、拒单数、待执行意图压力和现金拖累。
- 起始日期敏感性分析入口。
- HFQ 数据链校验入口。
- 平台市场数据同步入口。行情快照随 git 版本管理，同步采用**稳定写盘**：未变行保留原 `updated_at`、volume/amount 在 1% 容差内视为主备源噪音不算变化、保留文件原有行尾、内容一致时不写盘——`git diff` 只反映真实数据变化（共享函数 `data_store.write_csv_stable`，合成 3X 生成器同用）。**注意：只应在收盘后同步/提交快照**——盘中同步会把半日 K 线写进快照（曾发生），晚间同步会以小 diff 形式自动修正。
- 分红/拆分事件表是**只增不删的账本**（`corporate_actions.merge_event_table`）：上游返回缺失或键冲突时保留本地已验证事件并打警告；新拆分事件必须先通过价格交叉验证（拆后首日价 ≈ 拆前价 ÷ 比例，±15%）才会入表——曾拦下上游把 510500 两条已验证拆分替换成错误 1:0.01 的事故。
- 实盘镜像组合闭环（`platform/src/platform_core/live.py` + `notify.py` + `scripts/run_live_cycle.py`）：`reconcile` 导入真实持仓+现金覆盖组合状态并记录真实净值（mark-to-real，误差每日清零不累积）；`plan` 用真实权重+最新数据算目标，对执行引擎做 dry-run（整手取整/现金上限/费用与回测同口径）产出人可照做的"明日下单票"（`tickets/ticket_<date>.csv/.txt`），绝不模拟成交；`cycle` 一键编排 sync→reconcile→plan→每日估值→notify（非交易日自动跳过），推送支持 Server酱/SMTP（环境变量 `RQ_SERVERCHAN_KEY` 或 `RQ_SMTP_*` 零配置启用，失败不中断主流程）。每个交易日按收盘价对真实持仓 mark-to-market 并追加进 `real_nav.csv`（真实净值日频序列，供月度归因与组合列表页使用）；推送分两条——markdown 组合日报（总值/日变动/现金/各资产权重/阈值带状态）交易日必发，触发调仓时下单票作为独立第二条。产物在 `results/live_portfolios/<id>/`。`cycle --shadow <sim_id>` 可让影子模拟组合每交易日增量跟跑（`SimPortfolio.load()` 从持久化状态恢复）。
- 实盘月度归因（`platform/src/platform_core/attribution.py` + `scripts/report_live_attribution.py`）：对齐真实 `real_nav.csv` 与影子组合净值，输出区间收益差、年化 tracking error 与粗拆（现金拖累差 + 执行/结构残差），**只记录不改持仓**；收益观测不足 5 个判"样本不足仅存档"。报告写入 `reports/live/`（含真实账户金额，已 gitignore 不入库）。
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

## 常用入口

从仓库根目录运行：

```powershell
.\env\Scripts\python.exe platform\scripts\run_platform_backtest.py --config configs\baseline_r1_domestic_rolling.yaml --start-date 2019-02-28 --end-date 2025-06-30
.\env\Scripts\python.exe platform\scripts\run_platform_experiment.py --config configs\baseline_r1_domestic_rolling.yaml --start-date 2019-02-28 --end-date 2025-06-30
.\env\Scripts\python.exe platform\scripts\run_sensitivity.py --config configs\baseline_r1_domestic_rolling.yaml --end-date 2025-06-30
.\env\Scripts\python.exe platform\scripts\sync_platform_data.py --config configs\baseline_r1_domestic_rolling.yaml
.\env\Scripts\python.exe platform\scripts\sync_all_market_data.py
.\env\Scripts\python.exe platform\scripts\get_common_date_range.py --config platform\configs\baseline_r1_domestic_rolling.yaml
.\env\Scripts\python.exe platform\scripts\run_sim_portfolio.py --config configs\baseline_r1_domestic_rolling.yaml --checkpoint <checkpoint.json> --asof-date <YYYY-MM-DD>
.\env\Scripts\python.exe platform\scripts\run_dashboard.py
.\env\Scripts\python.exe platform\scripts\run_live_cycle.py reconcile --config configs\baseline_r1_domestic_rolling.yaml --holdings <holdings.csv> --cash <float> [--asof-date YYYY-MM-DD]
.\env\Scripts\python.exe platform\scripts\run_live_cycle.py plan --config configs\baseline_r1_domestic_rolling.yaml [--asof-date YYYY-MM-DD] [--notify]
.\env\Scripts\python.exe platform\scripts\run_live_cycle.py cycle --config configs\baseline_r1_domestic_rolling.yaml [--sync] [--notify] [--holdings <csv> --cash <float>] [--force] [--shadow <sim_id>]
.\env\Scripts\python.exe platform\scripts\report_live_attribution.py --live-id <live_id> --shadow-id <sim_id> [--month YYYY-MM] [--notify]
```

上述命令默认使用 venv/uv 布局的 `.\env\Scripts\python.exe`；如果本地环境使用 conda/root 布局，可等价替换为 `.\env\python.exe`。

看板默认端口 8501，可用 `PORT` 环境变量覆盖。实盘 `run_live_cycle.py` 的持仓文件表头为 `code,quantity[,cost_basis]`；`reconcile`/`plan` 单独使用时先同步行情（否则被 7 天数据新鲜度闸门拦下），`cycle --sync` 会自动同步；每个工作日收盘后定时跑 `cycle --sync --notify` 的任务计划注册命令见脚本 docstring。

平台脚本会把工作目录切到 `platform/`，因此脚本参数中的 `configs/`、`data/`、`results/` 等相对路径均按平台目录解析。

## 研究验收规则

- 研究、参数选择、ETF 篮子选择、候选过滤和结论写作只能使用 `2025-06-30` 及以前的数据。
- `2025-07-01` 及以后是固定最终测试样本，只能在候选策略、参数、篮子、再平衡规则和验收阈值冻结后使用。
- 正式提交平台研究结果前，必须在训练样本内对基线和候选做比较，并运行起始日期敏感性。
- 起始日期敏感性应从最早共同可用交易日到 `2025-06-30`，每 2 个自然月生成一个 `start_date`，每次回测截止到 `2025-06-30`。
- 报告必须读取实际 artifact，优先读取 `metrics.json`，不能凭记忆推断指标。
- 如果存在回测 artifact，报告必须包含换手率、交易数、订单数和拒单数。
- 新生成的 markdown 报告和总结必须使用中文；代码标识符、文件名、metric key 和命令保持原文。

## Artifact 位置

- 直接回测原始结果：`platform/results/backtests/<run_id>/`
- 标准实验原始结果：`platform/results/backtests/<experiment>/<timestamp>/<strategy>/<run_id>/`
- 标准实验报告：`platform/reports/experiments/<experiment>/<timestamp>/`
- 敏感性原始结果：`platform/results/sensitivity_raw/<strategy>/<timestamp>/`
- 敏感性报告：`platform/reports/sensitivity/<strategy>/<timestamp>/`
- 数据校验报告：`platform/reports/data_validation/<timestamp>/`

原始结果目录保存执行级 artifact；报告目录保存决策级摘要、指标、配置副本和原始路径引用。
