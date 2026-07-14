# Platform 下一阶段建设蓝图（实战环路 · 看板升级 · 策略扩展）

> 撰写时间：2026-07-05
> 撰写者：Claude Fable 5（架构评审 + 交接文档）
> 面向读者：后续接手本项目的 AI 模型（Opus 4.8 等）与开发者本人
> 阅读顺序：`AGENTS.md`（工作纪律，最高优先） → `platform/docs/current_platform.md`（现状） → 本文（怎么继续建）

---

## 0. 本文定位

用户的最终目标是：**平台在调仓日主动推送"明日下单票"，用户照单下单；定期用真实账户数据修正平台状态；平台还能承载 LLM 生成的新策略。**

本文给出达成该目标的完整施工蓝图：优先级、模块规格、数据契约、验收标准、明确不做的事。后续模型请按主线 A → B → C 的顺序施工，每条主线内部按编号顺序。**动手前先读 `AGENTS.md` 的 Hard Rules，本文与其冲突时以 `AGENTS.md` 为准。**

---

## 1. 项目定位与工程尺度（总则）

这是**个人使用（或极小范围）的投资决策辅助系统**，不是产品。工程尺度按以下标准把握：

**应该做的：**
- 清晰的模块边界（现有的 strategy / execution / engine / sim 分层已经很好，保持）。
- 每个新功能有数据契约（文件 schema 写进文档）和至少一个 pytest 用例。
- 状态文件（`portfolio_state.json` 等）向后兼容：加字段可以，改字段名/删字段必须写迁移。
- 一切产物落盘为人可读的 CSV/JSON/Markdown，便于出问题时手工核对。

**不应该做的（过度工程化红线）：**
- 不引入 Web 后端框架（FastAPI 等）、消息队列、Docker、微服务。Streamlit 看板 + 命令行脚本 + Windows 任务计划就是全部运行时。
- 不做用户系统、权限、多账户抽象（真到需要多账户那天再说）。
- 不换数据库。SQLite + CSV + JSON 已够用十年。
- 不做策略沙箱/动态文件加载/hash 防篡改（RetailQuant 旧文档里的设计）。策略就是仓库里的 Python 类，git 就是版本管理，SQLite 的策略版本表做引用保护已足够。
- 不为"未来可能支持期货/加密货币"预留抽象层。等真要支持时按 `planned_features.md` 的 AssetAdapter 思路再加。

**判断准则：一个改动如果不能在两周内被单人（或单个 AI 会话）完成并验收，就拆小或砍掉。**

---

## 2. 对 `RetailQuant_技术设计文档.md` 的裁决

仓库根目录的 `RetailQuant_技术设计文档.md` 是最早的愿景文档（v0.1-draft）。**裁决：定性为历史文档，不再作为施工依据。** 现有 `platform/` 的架构在多个关键点上**优于**该文档，不要向旧文档回退：

| 旧文档设计 | 现平台设计 | 裁决 |
|-----------|-----------|------|
| 策略输出 BUY/SELL Signal（信号式 DSL） | 策略只输出目标权重 `TargetPortfolio`，订单由执行层派生 | **保持现设计。** 目标权重契约更简洁、天然支持 rebalance 类策略、执行细节（手数/涨跌停/费用）与策略解耦。这是全平台最重要的抽象，不许动。 |
| 策略为独立 .py 文件 + hash 校验 + 沙箱加载 | 策略为 `strategy.py` 内注册的类 + SQLite 版本表 | 保持现设计，见 §1 红线。 |
| 多资产雄心（美股/期货/加密/场外基金/基本面） | A 股 ETF 日频 | 保持收缩。用户实际策略是 ETF 永久组合 + rebalance，旧文档的资产矩阵是伪需求。个股支持见主线 C。 |
| akshare/tushare/yfinance/ccxt 四数据源适配 | finshare 单源 + 本地 CSV | 保持现设计。单源够用；数据新鲜度闸门（AGENTS.md）比多源更重要。 |
| quantstats 生成报告 | 自研 metrics.py + 中文报告 | 保持现设计。指标口径自己可控、可审计。 |
| 冷却池、策略分段切换、导入导出 bundle | 冷却池已有；分段切换被 Hard Rule 8 明确禁止；bundle 未做 | 分段切换不做；bundle 不做（个人使用，git + 文件备份足够）。 |

旧文档中**仍然有效**并已被现平台吸收的思想：次日开盘执行避免未来函数（`signal_execution_lag_days=1`）、手续费必须建模、checkpoint 可恢复、涨跌停/停牌/未成交重试。

**完成度结论：** 相对旧文档全量范围约 40%，但相对"用户真实需要的子集"约 75–80%。缺口不在回测（回测已超出旧文档质量：分红/拆股/滑点场景/敏感性分析都是旧文档没有的），而在**实战环路**（主线 A）——这正是下一阶段的全部重点。

---

## 3. 现状快照（2026-07-05，commit 47e038d 附近）

已具备（细节见 `current_platform.md`）：
- 日频事件驱动回测引擎，含分红/拆股/涨跌停/停牌/lot size/费用/三滑点场景。
- 11 个内置策略（等权 + risk parity 家族），注册表 `get_strategy_class()`。
- checkpoint 全量组合状态持久化；`SimPortfolio.advance()` 可从 checkpoint 增量推进（纸面自动撮合模式）。
- SQLite 元数据：策略版本、回测记录、sim 组合、引用保护。
- 标准实验/起始日期敏感性/数据校验入口；中文报告纪律。
- Streamlit 只读看板（概览/配置/回测分析三页，净值+回撤+持仓+订单表）。

主要缺口（即本蓝图三条主线）：
- **A. 实战环路**：无"明日下单票"渲染；无真实持仓回灌（mark-to-real）；无推送通知；无定时任务；无模型 vs 真实净值归因。
- **B. 看板**：无多尺度收益视图（日/月/年收益、滚动指标、区间缩放）、无多回测对比、看不到 sim/实盘组合。
- **C. 策略扩展**：LLM 生成策略的注册流程未成文；个股所需的卖出印花税、数据源未支持。

---

## 4. 不动摇的架构契约

后续任何施工不得破坏以下五条（破坏 = 大范围返工）：

1. **策略只产出目标权重。** `Strategy.generate_targets(context) -> TargetPortfolio | None`。任何"策略直接下单/直接改仓位"的需求都要改写为权重表达。
2. **T 日信号、T+1 执行。** 意图以 `PendingIntent(created_date=T)` 存入 state，`created_date < current_date` 才可执行。实战环路同样遵守：今晚生成的票，明天执行。
3. **执行细节全部在 `execution.py`。** 手数取整、现金上限、涨跌停、费用、滑点，策略层和实战层都不得自己算成交，需要模拟成交时复用 `ExecutionEngine.apply_target()`。
4. **状态即真相，且可整体序列化。** `PortfolioState.to_dict()/from_dict()` 是唯一的状态存取通道；实战回灌 = 构造一个新的 `PortfolioState` 覆盖写入，不做增量 patch。
5. **数据纪律不因实战松动。** 研究/调参仍只用 2025-06-30 以前数据；实战用最新数据不算违规（那是应用不是研究），但实战期间产生的观察不得反过来用于改参数后声称"研究结论"。

---

## 5. 主线 A：实战环路（优先级 P0）

### 设计总纲：mark-to-real

风险平价/等权 rebalance 都是**目标权重型**策略：只依赖"最新行情 + 当前权重"，不依赖持仓路径。因此实盘环路选择**让模型每天对齐现实**，而不是让现实去对齐模型：

```
每个交易日收盘后：
  ① sync 行情数据
  ② reconcile：用户提供真实持仓+现金 → 覆盖写入 live 组合 state（真值重置）
  ③ plan：策略基于真实权重+最新数据算目标 → 渲染"明日下单票"
  ④ notify：推送下单票（无调仓则推送"今日无操作"或静默）
次日：用户照票下单（成交价/股数有偏差无所谓）
当晚：回到 ①，误差被真值重置吸收，永不累积
```

推论：**不需要"定期误差抹平"功能。** 整手取整、几个 bp 价差落在策略的 `rebalance_threshold`/`weight_tolerance` 无交易区内，会在下次超阈值时一并修正。用户要的"用现实数据修正回放"入口，就是 ② reconcile 本身。

### A1. 实盘镜像组合 `LivePortfolio`（已完成最小闭环，2026-07-05）

**竣工说明（as-built，与下方原规格的差异）**：已实现 `platform/src/platform_core/live.py`（`reconcile` + `plan` + 下单票渲染）与入口 `platform/scripts/run_live_cycle.py`（`reconcile`/`plan` 子命令），测试在 `test_platform_live.py`。三处实现决策：
1. **未接 SQLite store**（最小闭环文件即真相，元数据集成留待 A4 一起做）；
2. 票面估价强制用 plan 日**收盘价**（覆盖配置的 `execution_price_field`）；
3. **数据末日日历补丁**：实盘 plan 时 plan 日必然是数据最后一天，而 `is_month_end()` 等节奏判断把"日历末日"当月末，月频策略会天天触发。已在 plan 内给日历补一个"下一工作日"近似未来日，使实盘节奏与回测一致（极端情形：月末最后几个交易日全是节假日时当月触发顺延，可接受）。后续实现 A3/A4/A5 沿用以下原规格。

原规格：

与 `sim.py` 的 `SimPortfolio`（纸面自动撮合）是**两套环路**，不要合并成一个类加 if 分支。`LivePortfolio` 不自动撮合任何订单——现实才是撮合引擎。

```python
class LivePortfolio:
    """实盘镜像组合。目录 results/live_portfolios/<portfolio_id>/"""

    @classmethod
    def create(cls, portfolio_id, config, store) -> "LivePortfolio": ...

    def reconcile(self, holdings_csv: Path, cash: float, asof_date: date) -> None:
        """真值重置：由券商导出/手抄的真实持仓构造全新 PortfolioState 覆盖写入。
        - positions 由 holdings_csv 构造（code → asset_id 映射取自 config）
        - cash 为参数传入（券商 App 可直接看到）
        - pending_intents 清空（昨天的票现实已处理完毕）
        - strategy_state 保留与否无所谓：risk parity 族从行情历史重算，不依赖它
        - 追加一行到 real_nav.csv：date, cash, positions_value, total_value（用收盘价估值）
        """

    def plan(self, asof_date: date) -> PlanResult:
        """生成明日下单票，不改真实持仓：
        1. 用截至 asof_date 的数据构造 StrategyContext，调 generate_targets()
        2. 若返回 None：无调仓，写空票并返回
        3. 若有目标：deepcopy(state) 后调 ExecutionEngine.apply_target() 做 dry-run，
           丢弃被修改的副本，只取返回的 orders 列表 —— 由此免费获得手数取整、
           现金上限、weight_tolerance 无交易区、费用估算，与回测口径完全一致
        4. 写 results/live_portfolios/<id>/tickets/ticket_<date>.csv 和 .txt
        """
```

价格基准说明：票面股数按 asof 日收盘价估算，次日实际成交价会有偏差——这正是阈值带要吸收的东西，票面注明"股数为估算，按券商实际可买数量就近取整即可"。

**验收：** pytest 覆盖 reconcile（CSV → state 正确、real_nav 追加）与 plan（有/无目标两分支；dry-run 不改 state_path 落盘内容）；手工端到端一次：造一份假持仓 CSV → reconcile → plan → 检查 ticket 文件人可读、股数是整手。

### A2. 下单票契约（已随 A1 实现，2026-07-05；CSV 列与 TXT 版式按本节契约落地）

`ticket_<date>.csv` 列：

```
date, asset_id, code, name, side, quantity, est_price, est_value,
weight_before, weight_target, est_fee, note
```

`ticket_<date>.txt`（推送正文，人可直接照做）示例：

```
【调仓单】2026-07-06 执行（基于 07-05 收盘估算）
组合: r1_domestic_rolling | 总值 ≈ 1,203,450 元
1. 卖出 511260 十年国债ETF   3,700 股 ≈ 44,penny 元（28.1% → 24.5%）
2. 买入 518880 黄金ETF       5,300 股 ≈ 38,690 元（12.0% → 15.2%）
现金余量 ≈ 2.1%。股数为估算，成交价偏差无需在意，下次调仓自动修正。
```

无调仓日的正文固定为一行："【无操作】<date> 组合权重在阈值带内，今日无需交易。"

### A3. 通知模块（已完成，2026-07-05）

**竣工说明**：`notify.py` 已实现，Server酱 + SMTP 双渠道，`send_notification()` 永不抛异常。比原规格多一项：**渠道零配置自动发现**——设了 `RQ_SERVERCHAN_KEY` 或 `RQ_SMTP_HOST/USERNAME/PASSWORD/TO` 环境变量即自动启用对应渠道，YAML 里的 `notify.channels` 块变成可选的显式覆盖（存在时优先）。原规格：

- 接口：`def send_notification(title: str, text: str, config: dict) -> bool`，失败打日志返回 False，**绝不抛异常中断主流程**（票已落盘，推送失败无非手动去看）。
- 首选实现两个渠道即可：**Server 酱（微信）** 和 **SMTP 邮件**（互为备份，都是 ~30 行的 HTTP GET / smtplib）。Telegram/企业微信等以后按需加。
- 密钥走环境变量（如 `RQ_SERVERCHAN_KEY`），配置文件里只写渠道名，**密钥不入库不入 git**。

### A4. 统一入口脚本 + 调度（已完成，2026-07-05）

**竣工说明**：`run_live_cycle.py` 三个子命令齐了（reconcile/plan/cycle）。`cycle` = （`--sync` 或 config `data.fetch` 时）同步行情 → （给了 `--holdings --cash` 时）reconcile → plan → **每日估值** → （`--notify` 时）推送；asof 不在交易日历（周末/节假日/数据未更新到当日）时直接跳过不重复出票，`--force` 可强制按最近交易日出票。编排逻辑在 `LivePortfolio.cycle()`（notifier 可注入，便于测试）。任务计划注册命令见脚本 docstring。

**2026-07-11 增补（每日日报）**：`cycle` 每个交易日对真实持仓按收盘价 mark-to-market 并追加进 `real_nav.csv`——持仓只经 reconcile 变化，所以"上次对齐持仓 × 今日收盘"即真实日频净值（当日已交易未对齐的情形在下次 reconcile 自愈）。推送拆为两条：markdown 组合日报（总值/较上一估值日变动/现金/各资产权重/阈值带状态，Server酱 desp 按 markdown 渲染）交易日必发；触发调仓且有可执行订单时，下单票作为独立第二条，避免被日报淹没。已在真实组合上验证（Server酱 + Gmail SMTP 双通道）。原规格：

```
run_live_cycle.py reconcile --portfolio <id> --holdings <csv> --cash <float> [--asof-date d]
run_live_cycle.py plan      --portfolio <id> [--asof-date d] [--notify]
run_live_cycle.py cycle     --portfolio <id> --holdings <csv> --cash <float> [--notify]
    # cycle = sync 该组合行情 → reconcile → plan → notify；非交易日直接退出
```

调度用 Windows 任务计划（`schtasks`）每个工作日 16:30 跑 `cycle`。但注意 reconcile 需要人先提供当日真实持仓——**推荐的现实节奏**是：平时让任务计划只跑 `plan --notify`（用上一次 reconcile 的 state，权重漂移极慢，无伤大雅），用户每次**实际下过单之后**手动跑一次 reconcile 对齐真值。这样自动化和人工录入解耦，不会因为忘了导持仓而整条链路卡死。

`real_holdings.csv` 契约（用户手工维护，或从券商导出后整理）：

```
code, quantity            # 可选第三列 cost_basis，缺省则沿用估算
511260, 12000
518880, 21000
```

### A5. 月度净值归因（已完成，2026-07-11）

**竣工说明**：主线 A 至此全部完成。
- 归因核心在 `platform/src/platform_core/attribution.py`（可测试的纯函数），CLI 为 `scripts/report_live_attribution.py`（默认出上个自然月，`--month` 指定，`--notify` 推送）；
- 影子接线：`run_live_cycle.py cycle --shadow <sim_id>` 每交易日把影子模拟组合增量推进到 plan 日（新增 `SimPortfolio.load()` 从持久化状态恢复，区别于回到 checkpoint 重放）；影子失败只提示、不阻断日报环路；
- 归因粗拆口径：现金拖累差 =（真实平均现金权重 − 模型平均现金权重）× 模型区间收益（近似），其余归入"执行与结构差异"残差——真实侧无逐笔费用明细，再细拆是伪精度；收益观测 < 5 判"样本不足仅存档"；
- **报告含真实账户金额，`platform/reports/live/` 已 gitignore 不入库**；
- 建议配套：每月 1 日 20:00 的任务计划（注册命令见脚本 docstring）。

原规格：

- 输入：`real_nav.csv`（真实） vs 同期纸面 `SimPortfolio` 的 `nav.csv`（模型）。
- 输出：`platform/reports/live/<YYYY-MM>_attribution.md`（中文），内容：两条净值曲线对比、月度 tracking error（bp）、差异归因粗拆（手续费差/成交价差/现金拖累），**只记录，不据此改持仓或改参数**。
- 前提是同一 checkpoint 起点同时维护一个纸面 sim 组合作为影子——`run_live_cycle.py cycle` 里顺带 `SimPortfolio.advance()` 推进影子组合即可。

---

## 6. 主线 B：看板升级（优先级 P1）

现状：Streamlit + Plotly 完全够用，**不要换框架**。问题只是图表规格太素。改动集中在 `platform/src/platform_dashboard/`。

### B1. 收益多尺度视图（已完成，2026-07-05）

已在 `app.py` 的"净值与回撤"/"收益分解"两个标签页落地：净值/收益率双显示模式 + 区间选择（近1月～近3年/今年/全部）、对数坐标、基准对比与超额曲线、月度收益热力图（红涨绿跌）、年度收益、日收益分布、月度收益序列、滚动 60 日波动 / 252 日 Sharpe。全部从 `nav.csv` 派生，引擎零改动；派生计算在 `artifacts.py`（`nav_analytics` / `rebase_benchmark` / `window_start_date`）。

**记录一个设计取舍（后续别改回去）**：区间切换最初尝试用 Plotly 图内 `rangeselector` 按钮，后放弃——那是前端纯视觉缩放，无法把曲线重新归零到区间首日（做不了"近1月从 0% 起算"），且按钮与图例在图顶重叠。最终方案是 Streamlit 侧的"显示 + 区间"控件：切换触发页面重跑并重算 rebase（毫秒级，缓存兜底），回测分析页与回测对比页共用同一套控件语言和 `window_start_date()` 口径。

### B2. 多回测对比页（已完成，2026-07-05）

已落地：`st.multiselect` 选 2–5 个 run，`align_navs()` 裁剪到共同重叠区间（可选）并在所选区间首日各自归一（净值模式从 1.0、收益率模式从 0% 出发），净值/回撤叠加 + 全样本指标对照表。区间与显示控件与 B1 完全一致。

### B3. 模拟/实盘组合页（已完成，2026-07-15）

**竣工说明（as-built，与下方原规格的差异）**：发现器合并为一个 `discover_portfolios()`（live 在前）；sim 全史 = 拼接 `runs/*/nav.csv` 增量段、同日保留最新段，统一归一为 `net_value` 列（`read_portfolio_nav`）。目标权重优先取 `pending_intents`，否则取最近一张下单票的 `weight_target`（票只含需交易资产，图注已说明）；非行情代码（演示组合）跳过取价，权重留空。real_nav vs 影子 sim 用 `align_navs` 在共同区间首日归一（收益率口径）。组合目录无元数据（A1 有意未接 SQLite），策略名列暂缺。原规格：

- 发现器：`artifacts.py` 加 `discover_sim_portfolios()` 与 `discover_live_portfolios()`，分别扫 `results/sim_portfolios/` 与 `results/live_portfolios/`。注意 sim 的 `nav.csv` 列是 `total_value` 而非回测的 `net_value`，读取层要归一。
- 展示：当前权重 vs 目标权重（双色条形图）、pending intents 表、最近一张下单票原文、real_nav vs 影子 sim nav 对比曲线。
- 保持**只读**。reconcile 录入仍走命令行，看板不做写操作（避免把看板变成需要认真测试的应用）。

### B4. 组合总览列表页（已完成，2026-07-15）

**竣工说明**：`trailing_returns`（复用 `window_start_date`，新增"近1周"标签；历史短于区间显示 —，另附"成立以来"）+ `business_days_behind`（工作日近似交易日，未剔除节假日，>=3 整行标黄）。上线当天即抓到真实故障：影子组合净值滞后 3 个工作日（任务计划 `--shadow` 参数被 schtasks 261 字符上限截断）。原规格：

投资者日常最高频的问题是"我所有在跑的组合最近表现如何"，一页列表回答它：

- 一行 = 一个在运行的 sim/live 组合：名称、策略、最新净值日期、**近 1 周 / 1 月 / 3 月 / 半年 / 今年收益**、区间最大回撤、当前 pending intents 数。
- 近 N 期收益就是 nav 序列的两点回看（`nav[t] / nav[t-N交易日] - 1`），**在读取时现算即可，不需要预计算表**：个人规模（≤ 几十个组合 × 数千行 nav.csv）是毫秒级 pandas 操作，加上 `st.cache_data` 之后交互内零重复计算。
- **净值的"新鲜度"不由看板负责**：nav 是否更新到昨天，取决于主线 A4 的每日定时任务跑 `advance()`/`plan()`。看板保持只读，但列表必须显示 `last_date`，并把落后当前日期 3 个交易日以上的组合高亮标黄——这是发现"定时任务挂了"的最廉价手段。

### 性能预算与优化顺序（给后续开发者，防过早优化）

当前代码唯一的潜在慢点是 `discover_runs()`：启动时对 `results/` 下每个 manifest 全量重算 `build_platform_metrics()`（逐 run 读 4–5 个 CSV）。3 个 run 无感；到 ~50 个 run 会出现秒级启动延迟。届时按以下顺序逐级优化，**不要提前做后面的**：

1. run 目录里已存在 `metrics.json` 时直接读取，跳过重算（一行判断，收益最大）。
2. 列表页场景只需 nav 尾部数据时，用 `pd.read_csv(usecols=...)` + 尾部截取代替全表加载。
3. `st.cache_data` 已挡住会话内重复计算，确认缓存键含 mtime 即可（现状已是）。
4. 真到几百个 run，再把 metrics 写入 SQLite 做索引——个人使用规模大概率永远走不到这一步。

**验收：** 每个图有空数据兜底（现有 `st.info` 风格）；`cached_*` 缓存签名带 mtime 以便刷新；手工跑 `run_dashboard.py` 检查三页。

---

## 7. 主线 C：策略扩展（优先级 P2）

### C1. LLM 生成策略的标准注册流程（成文即完成大半）

目标形态就是用户说的"大模型生成策略函数，注册到项目"。流程固化为：

1. 新策略写成 `Strategy` 子类，实现 `generate_targets(context) -> TargetPortfolio | None`（能读 `context.data` 的历史窗口、`context.state` 的当前持仓）。
2. 放置位置：建议新建 `platform/src/platform_core/strategies/` 包，每个策略一个文件，`strategy.py` 只保留基类、`StrategyContext`、注册表和 risk parity 家族（1458 行已经太大，**新策略一律不再往里加**；旧策略搬迁可做可不做，别专门发起大重构）。
3. 在 `BUILTIN_STRATEGIES` 注册（仅当确实要被 config 加载，Hard Rule 3）。
4. 必须附带：一个 pytest（合成数据上目标权重合法：非负、和 ≤1）+ 一次对基线的标准实验（`run_platform_experiment.py`）+ 起始日期敏感性，按 `AGENTS.md` 验收后才算入库。
5. 研究失败的策略从注册表移除，结论写 `research-dashboard/notes/`。

### C2. 个股支持的三个前置条件（做之前逐项确认）

平台模型层其实已兼容个股（`Asset` 有 `lot_size`、`price_limit_pct`、停牌、涨跌停都在），真正缺的是：

1. **卖出印花税**：`FeeProfile` 目前单一费率。改为 `buy_rate` / `sell_rate`（A 股卖出加 0.05% 印花税），`execution.py` 按 `side` 取费率。这是唯一必须的引擎改动，很小。
2. **个股行情数据**：确认 finshare 数据源能拉个股日线并接入 `sync_all_market_data.py`；注意退市股（幸存者偏差）——个股策略的回测结论要额外声明样本里有没有退市标的。
3. **T+1 卖出限制未建模**：当日买入不能当日卖出。对月度/阈值 rebalance 无影响（换手极低），文档声明即可，不建模。

个股"选股"策略同样表达为目标权重（选出的股票各占多少权重，未选中为 0），不需要新的策略接口。

---

## 7.5 主线 D：行业 ETF 动量轮动卫星仓（R039，2026-07-12 立项，**当日 D1 验收 Failed**）

用户决定在 R038 核心仓之外新开一条**高波卫星仓**策略线：行业 ETF 横截面动量轮动（1M+3M 混合动量、Top-3 等权、排名缓冲带、负动量持币，月频）。完整施工蓝图独立成文：**`platform/docs/r039_rotation_blueprint.md`**（策略规格、标的池准入、验收标准、D1–D4 迭代路线、明确不做清单）。要点：

- 遵循本蓝图 C1 流程：策略放 `strategies/rotation.py`，注册 + pytest + 标准实验 + 敏感性全套验收。
- 与核心仓在**组合层**隔离（独立 `sim_r9_*`/`live_r9_*` 命名空间），不动摇 §4 五条架构契约。
- 信号选型依据 2026-07-12 文献调研：A 股个股月频动量失效（Liu-Stambaugh-Yuan 2019）但行业动量存活；舆情/热点不做买入信号（日频动量一周内反转），其可交易本质由拥挤度代理（D2 迭代）。

**竣工说明（as-built，2026-07-12）**：D1 当日完成实现+全套验收，训练样本相对行业等权基线年化落后 10.5pp、32 个起点仅 1 个为正，判 **Failed / research-only**（详见 r039 蓝图头部判定与 `reports/r039_industry_rotation_report.md`）。策略已撤销注册（代码与 pytest 保留）；沉淀资产：16 只行业 ETF 全量数据链（sina 行情 + 事件驱动 hfq 因子 + 分红/拆分事件表扩容）、可复用基线 `domestic_industry_equal_weight.yaml`、`MarketDataStore` 历史收缩保护。卫星仓诉求仍在，下一个候选建议"行业池等权 + Swedroe 阈值带"（新编号立项）。

---

## 8. 明确不做清单（后续模型请勿"顺手"实现）

- 自动交易/券商 API 对接下单（合规和风险都不值得，人工照票下单是特性不是缺陷）。
- 分钟级/实时行情、盘中信号。日频是刻意选择。
- 期货、加密货币、美股、场外基金（`planned_features.md` 有思路，但无用户需求不启动）。
- 策略文件沙箱、hash 防篡改、导入导出 bundle。
- 看板写操作、Web 部署、多用户。
- 用深度学习/强化学习做策略（Hard Rule 4）。

---

## 9. 附录

### 9.1 环境与文档坑（实测核对于 2026-07-05）

- **Python 解释器允许两种本地布局**：uv/venv 布局使用 `env\Scripts\python.exe`，conda/root 布局使用 `env\python.exe`。活文档（`AGENTS.md`/README/docs/SKILL.md）中的命令优先展示 `env\Scripts\python.exe`，但可按本机布局等价替换；`platform/reports/`、`research-dashboard/notes/` 等历史报告中的旧命令未改（历史产物不回写），复制历史报告里的命令时注意按本机布局替换。
- 平台脚本会把 cwd 切到 `platform/`，参数里 `configs/ data/ results/` 相对路径按 platform 目录解析。
- 回测前先 `sync_all_market_data.py`，否则数据新鲜度闸门（7 天）会拦截。
- 部分文档提到的 `baseline_mvp_equal_weight.yaml` 等旧配置名已不存在，现行基线是 `baseline_r0/r1_*` 系列，以 `platform/configs/` 实际文件为准。

### 9.2 关键数据契约速查

- `portfolio_state.json`：`cash, positions{asset_id→{quantity,cost_basis}}, pending_intents{...}, cooldown_pool, strategy_state, last_date, dividend_receivables` —— 见 `models.py:PortfolioState.to_dict()`。
- 回测 `nav.csv` 用 `net_value` 列；sim 的 `nav.csv` 用 `total_value` 列（历史差异，读取层归一，勿改历史产物）。
- 下单票、real_holdings 契约见 §5 A2/A4。

### 9.3 建议施工顺序（每项一个独立会话/PR 即可完成）

1. ~~A1+A2：`live.py` 的 reconcile + plan + 下单票~~ **已完成（2026-07-05）**：`live.py` + `run_live_cycle.py`（reconcile/plan），端到端验证通过（真实配置 + 全真数据出票）。SQLite 集成与 notify/cycle 留给下一步。
2. ~~A3+A4：notify + cycle + 任务计划~~ **已完成（2026-07-05）**：`notify.py`（Server酱/SMTP，环境变量零配置自动发现）+ `cycle` 子命令（非交易日自动跳过）。任务计划命令已写进脚本 docstring，由用户设好推送密钥后自行注册。
3. ~~B1：收益多尺度视图~~ **已完成（2026-07-05）**：净值/收益率双模式（收益率按区间首日归零）、区间选择、对数坐标、基准对比与超额曲线、月度收益热力图、年度收益、日收益分布、月度序列、滚动波动与滚动 Sharpe，持仓面积图含现金层。派生计算在 `artifacts.py`（`nav_analytics`/`rebase_benchmark`/`window_start_date`），测试在 `test_platform_dashboard.py`。
4. ~~B3+B4：sim/实盘组合页 + 组合总览列表~~ **已完成（2026-07-15）**：`discover_portfolios`/`read_portfolio_nav`/`trailing_returns`/`business_days_behind` 等读取层 + "组合总览"/"组合详情"两页，测试在 `test_platform_dashboard.py`。**主线 B（看板升级）全部竣工。**
5. ~~A5：月度归因报告~~ **已完成（2026-07-11）**：attribution.py + report_live_attribution.py + cycle --shadow 影子跟跑；reports/live/ 因含真实账户金额已 gitignore。**主线 A（实战环路）全部竣工。**
6. ~~B2：多回测对比页~~ **已完成（2026-07-05）**：`align_navs` 对齐重叠区间、在所选区间首日归一叠加（净值/收益率双模式）+ 回撤叠加 + 指标对照表，控件与回测分析页统一。
7. C1 流程文档化 + C2（真要做个股时再启动）
