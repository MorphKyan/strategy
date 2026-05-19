# 散户多资产策略回测系统计划文档

日期：2026-05-16

## 1. 项目定位

目标不是先做一个“全市场高频量化平台”，而是做一个散户可验证想法的多资产、可复现、可导入导出的回测与模拟组合系统。

第一阶段优先支持：
- A 股、ETF、LOF、场外基金、可转债等日频或更低频资产。
- 基于日频收盘价、开盘价、复权价、基金净值、财务指标、估值指标的策略。
- 多策略分段执行、组合 checkpoint、冷却池、调仓约束、手续费、涨跌停不可成交等真实限制。

期货、期权、Web3 币种、实盘交易接口应作为扩展层接入，不应拖慢核心回测模型的落地。

## 2. 当前仓库现状

当前仓库已经具备：
- YAML 配置驱动的单策略回测入口：`main.py`。
- 本地 CSV 数据加载与自动补数据：`src/data_handler.py`。
- 简单组合再平衡引擎：`src/engine.py`。
- 策略模块动态加载：`src/strategies/<strategy>.py`。
- 风险平价研究报告与实验归档：`scripts/run_experiment.py`、`reports/experiments/`。

当前仓库缺少：
- 通用资产模型，无法统一股票、基金、期货、币种、现金、保证金资产。
- 通用订单、成交、撮合、涨跌停、停牌、滑点、手续费模型。
- 持仓快照、任意日期 checkpoint、从 checkpoint 接续回测。
- 模拟组合状态持久化和每日增量推进。
- 多策略时间段编排。
- 策略版本锁定、不可变发布、引用计数、删除/修改保护。
- 数据源抽象层和数据质量检查。
- 基本面/估值/财务指标的 point-in-time 处理，容易产生未来函数。
- 导入导出完整回测与组合档案的稳定格式。
- UI/API 层、任务队列、数据库 schema、权限与审计日志。

## 3. 推荐总体架构

建议采用“研究内核 + 状态服务 + 数据服务 + 策略插件”的结构。

核心模块：
- `data`: 数据源适配、数据标准化、交易日历、复权、财务数据时点处理。
- `domain`: 资产、账户、持仓、订单、成交、费用、策略版本、组合、回测记录。
- `engine`: 事件驱动日频回测引擎，支持 checkpoint 和多策略调度。
- `execution`: 撮合模型、涨跌停/停牌限制、滑点、手续费、成交失败后的重试或放弃规则。
- `strategy`: 用户策略接口、策略模板、策略版本管理、沙箱运行。
- `portfolio`: 模拟组合每日推进、状态保存、导入导出。
- `reporting`: 净值、回撤、交易、归因、换手、日志、可视化。
- `api/ui`: 本地 Web UI 或 CLI，先做本地单用户，后续再考虑多用户。

推荐存储：
- PostgreSQL 或 SQLite：存资产元数据、策略版本、组合、回测任务、checkpoint 索引。
- DuckDB + Parquet：存大规模行情、因子、财务面板数据，适合本地分析和批量回测。
- 文件归档：每次回测导出一个自包含目录，包含配置、策略版本 hash、输入数据版本、结果、日志。

## 4. 核心领域模型

### Asset

字段建议：
- `asset_id`: 内部唯一 ID，例如 `CN_STOCK:600519.SH`、`CN_FUND:161725.OF`、`CRYPTO:BTC/USDT:BINANCE`。
- `asset_type`: `stock`、`etf`、`lof`、`fund_otc`、`convertible_bond`、`future`、`crypto_spot`。
- `exchange`、`currency`、`lot_size`、`tick_size`、`price_limit_rule`、`fee_profile_id`。
- `tradable_start`、`tradable_end`、`status`。

### Bar / Factor / Fundamental

行情不要只存 close：
- 日频：`open`、`high`、`low`、`close`、`volume`、`amount`、`adj_factor`、`is_suspended`、`limit_up`、`limit_down`。
- 基金：`nav`、`acc_nav`、申赎状态、确认日、赎回到账延迟。
- 财务估值：`pe`、`pb`、`roe`、`debt_to_asset`、`dividend_yield`、公告日、报告期、生效日。

所有基本面数据必须按“当时可见”处理：
- 回测日只能看到已公告且已入库的数据。
- 不允许用财报报告期直接回填到过去。

### PortfolioState

字段建议：
- `cash`
- `positions`
- `pending_orders`
- `cooldown_pool`
- `strategy_runtime_state`
- `last_processed_date`
- `nav_history`
- `trade_history`
- `unfilled_intents`

checkpoint 应保存完整状态，而不只是持仓：
- 当前策略内部状态。
- 冷却池剩余天数。
- 未完成调仓意图。
- 成本价、可卖数量、冻结数量、费用累计。

### StrategyVersion

策略应分为“草稿”和“已发布版本”：
- 草稿策略可以修改、删除。
- 一旦被回测记录或模拟组合引用，就生成不可变版本。
- 已引用版本不能修改或删除，只能复制为新版本。
- 回测记录保存 `strategy_version_id`、源码 hash、参数、运行环境。

## 5. 策略编写方式建议

不要一开始做复杂 DSL。你的目标用户有一定编程能力，也会借助大模型，所以更适合“受约束的 Python 策略模板”。

推荐接口：

```python
from backtest_core import Strategy, Context, TargetPortfolio

class MyStrategy(Strategy):
    name = "low_pe_dividend_rebalance"
    version = "0.1.0"

    def initialize(self, context: Context):
        context.set_cooldown(days=20)
        context.set_rebalance_frequency("monthly")

    def before_trading_day(self, context: Context):
        pass

    def generate_targets(self, context: Context) -> TargetPortfolio:
        universe = context.assets.filter(asset_type=["stock", "etf"])
        candidates = universe.where(
            pe_lt=15,
            pb_lt=2,
            roe_gt=0.10,
            debt_to_asset_lt=0.60,
        )
        candidates = candidates.exclude_cooldown()
        return TargetPortfolio.equal_weight(candidates.top(20, by="dividend_yield"))

    def on_order_unfilled(self, context: Context, order, reason):
        return "retry_next_day"
```

为什么不先做纯逻辑表达式：
- 表达式适合简单筛选，例如 `pe < 15 and roe > 0.1`。
- 一旦涉及冷却池、分段策略、未成交处理、组合再平衡、基金申赎延迟，就会变成很难维护的半编程语言。
- Python 模板更容易让大模型生成、解释、测试，也能直接写单元测试。

可以提供两层能力：
- 低代码条件构造器：生成 Python 策略模板中的筛选条件。
- 高级 Python 策略类：允许用户直接写函数，但限制可访问 API，禁止随意读写系统文件、联网、修改数据库。

## 6. 回测引擎行为

推荐用事件驱动日频引擎，而不是完全向量化引擎作为主引擎。

每日流程：
1. 加载当日可见数据。
2. 更新持仓市值、现金、基金确认到账、期货保证金等状态。
3. 执行到期冷却池清理。
4. 根据策略时间表选择当前策略版本。
5. 策略生成目标组合或订单意图。
6. 风控与交易规则校验。
7. 撮合成交。
8. 未成交订单按规则进入 `retry_next_day`、`cancel` 或 `mark_failed`。
9. 生成 checkpoint。
10. 写入日志、净值、交易和持仓。

策略切换：
- 一个回测或模拟组合可以有多个策略段。
- 每个策略段包含 `start_date`、`end_date`、`strategy_version_id`、`params`。
- 切换日之前先完成上一策略的未完成订单处理，或者显式标记放弃。
- 新策略接收上一策略留下的完整 `PortfolioState`。

## 7. 涨跌停、停牌和未成交处理

必须建模，否则 A 股回测会明显偏乐观。

最低规则：
- 停牌：不可买、不可卖，价格沿用上一可交易日或按数据源标记。
- 涨停：默认不可买，可以卖。
- 跌停：默认不可卖，可以买。
- 一字涨跌停：按 `open == high == low == close == limit_price` 标记更严格。
- 成交量不足：按当日成交额或成交量设置最大参与比例，例如不超过当日成交额的 5%。

未成交处理应配置化：
- `retry_next_day`: 下个交易日继续完成调仓差额。
- `cancel`: 当日未成交即取消。
- `mark_failed`: 标记本次调仓未完全完成，后续报告中提示。

不要把“调仓动作”简单等同于“当天全部成交”。应该有 `RebalanceIntent` 和 `Order` 两层：
- intent 表示策略想达到的目标仓位。
- order 表示引擎尝试执行的具体买卖。

## 8. 手续费和滑点

不能直接去掉手续费。对低换手资产配置影响可能不大，但对条件单、止盈止损、轮动策略影响很大。

建议做成可版本化费用模型：
- A 股股票：佣金、最低佣金、印花税、过户费。
- ETF/LOF：佣金、最低佣金，通常无印花税。
- 场外基金：申购费、赎回费、持有期阶梯费率。
- 期货：按手数或成交额收费，保证金和合约乘数必须进入模型。
- crypto：maker/taker fee、提现不纳入回测主账。

MVP 可以先配置默认费率：
- `fee_profile` 存在数据库或 YAML。
- 每次回测保存 fee profile snapshot。
- UI 中明确标记“估算手续费”，后续允许用户按券商手动覆盖。

滑点建议从简单到复杂：
- MVP：按成交额固定比例，例如 5bp。
- 第二阶段：按成交额占当日成交额比例调整。
- 第三阶段：订单簿或分钟线模拟。

## 9. 数据源建议

公开或较易接入的数据源组合：

| 数据源 | 适合资产 | 优点 | 风险 |
|---|---|---|---|
| AKShare | A 股、ETF、基金、期货、债券、宏观等 | 覆盖广、Python 友好、开源 | 接口依赖公开网页，稳定性和字段变动要监控 |
| Tushare Pro | A 股行情、财务、估值、基金、指数等 | 结构化程度较好，有交易日历和财务数据 | 需要 token，部分接口有积分门槛 |
| 交易所官网 | 交易日历、规则、基础合约、官方公告 | 权威 | 接口不统一，工程成本高 |
| CCXT | crypto 现货/合约行情与交易所接口 | 统一大量交易所 API | 各交易所历史数据深度、费率、限流不同 |
| yfinance / Stooq | 海外股票、ETF、指数 | 易用 | 非中国市场为主，数据质量和授权需核对 |
| 券商/交易终端 API | 实盘账户、实盘委托、账户持仓 | 接近交易落地 | 接入门槛、权限、安全和稳定性要求高 |

建议 MVP 数据路线：
1. 先接 AKShare + Tushare Pro，覆盖 A 股、ETF、LOF、场外基金和基础财务指标。
2. 行情落地为统一 Parquet schema。
3. 基本面数据必须带公告日/可见日。
4. crypto 用 CCXT 作为第二阶段单独适配，不与 A 股交易日历混在一起。
5. 期货第三阶段接入，因为合约乘数、换月、保证金、夜盘和交割规则会显著增加复杂度。

## 10. 三方库取舍

推荐组合：
- DuckDB + Polars/Pandas：本地研究数据处理。
- VectorBT：用于快速信号研究、参数敏感性、向量化候选筛选。
- 自研事件驱动引擎：作为最终可复现回测和模拟组合主引擎。
- QuantStats 或 Empyrical：绩效指标计算可复用。
- Plotly/ECharts：回测报告和交互图。
- FastAPI + SQLite/PostgreSQL：本地服务和 UI API。

谨慎使用：
- Backtesting.py：适合单标的技术指标策略，不适合作为多资产组合再平衡主引擎。
- Backtrader：成熟但抽象较重，适合策略类风格；如果要做自己的 checkpoint、策略版本、组合状态服务，深度改造成本不低。
- QuantConnect LEAN：工程化、跨资产、C# 内核强，但中国本地数据、策略模板、产品化导入导出和本地自定义数据接入需要额外适配。适合参考模型，未必适合直接作为本项目内核。
- vn.py：更适合实盘交易接入、期货/CTP/券商网关和事件驱动交易，不建议作为第一版回测内核，但后续实盘层可以借鉴或接入。

## 11. 实盘交易衔接

短期不需要日内高频择时，但需要明确成交时点：
- 日频策略建议支持 `next_open`、`same_close`、`next_close` 三种撮合假设。
- 实盘模拟组合每天生成建议订单，不一定自动下单。
- 对接交易时优先做“开盘后一次/收盘前一次”的低频执行。
- 如果使用收盘价信号，真实执行应默认在下一交易日开盘或 VWAP/TWAP 窗口，不能假设当天收盘价成交。

实盘前必须补齐：
- 账户同步。
- 委托回报和成交回报。
- 手动确认模式。
- 最大单日交易额、最大持仓、黑名单。
- API key 加密和权限隔离。
- 异常熔断。

## 12. 导入导出格式

每个回测记录导出一个目录或 zip：

```text
backtest_<id>/
  manifest.json
  strategy_versions/
    strategy_<id>.py
    metadata.json
  config/
    backtest.yaml
    fee_profiles.yaml
    data_manifest.json
  checkpoints/
    2024-01-31.json
    2024-02-29.json
  results/
    nav.parquet
    positions.parquet
    orders.parquet
    trades.parquet
    metrics.json
    report.md
  logs/
    engine.log
```

`manifest.json` 需要包含：
- 系统版本。
- Python 版本。
- 数据版本/hash。
- 策略源码 hash。
- 配置 hash。
- 运行起止时间。

## 13. MVP 开发路线

### M0：现有仓库整理

目标：保留风险平价研究能力，同时新建通用平台目录。

任务：
- 新建 `docs/`、`src/core/`、`src/data_sources/`、`src/backtest/`、`src/strategy_api/`。
- 当前 `src/strategies/risk_parity.py` 保持不动。
- 增加 ADR：确认日频事件驱动引擎为主内核。

### M1：单账户、多资产日频回测内核

目标：能从初始持仓快照开始，跑 A 股/ETF 日频组合。

任务：
- 定义 `Asset`、`PortfolioState`、`Position`、`Order`、`Trade`。
- 支持现金、持仓、市值、净值。
- 支持固定费率和简单滑点。
- 支持涨跌停、停牌不可成交。
- 每日生成 checkpoint。
- 支持导出完整回测目录。

验收：
- 输入初始持仓快照。
- 策略按月调仓。
- 任意日期 checkpoint 可恢复并继续跑出一致结果。

### M2：策略类模板和策略版本管理

目标：用户可以写 Python 策略类，大模型可以按模板生成策略。

任务：
- 定义 `Strategy` 抽象类。
- 实现 `Context` 查询 API。
- 增加策略草稿、发布版本、源码 hash。
- 被组合或回测引用的版本不可修改或删除。
- 支持一个回测多个策略段。

验收：
- 回测记录中能查看每段策略和参数。
- 修改已引用策略时只能复制新版本。

### M3：数据源与基本面

目标：支持价格 + 估值 + 财务指标策略。

任务：
- 接 AKShare/Tushare 适配器。
- 标准化行情 schema。
- 标准化基本面 schema，加入公告日/可见日。
- 加入数据质量报告：缺失、停牌、复权异常、极端涨跌。

验收：
- 策略可以读取 PE、PB、ROE、资产负债率、股息率。
- 回测不会读取未来公告的数据。

### M4：模拟组合

目标：回测完成后可以转为模拟组合，并每日用新数据推进。

任务：
- 创建 `SimPortfolio`。
- 支持每日增量执行。
- 支持订单建议、成交确认、手动调整持仓。
- 支持从任意 checkpoint 派生新组合。

验收：
- 某个回测 checkpoint 可以生成模拟组合。
- 每天拉新数据后生成当日建议订单和最新净值。

### M5：更多资产扩展

目标：扩展但不污染核心模型。

任务：
- 场外基金：申赎确认日和赎回到账。
- 期货：合约乘数、保证金、换月、夜盘。
- crypto：7x24 日历、CCXT 行情、交易所 fee profile。

验收：
- 不同资产通过各自 `AssetAdapter` 和 `ExecutionModel` 接入。

## 14. 需要补充确认的问题

这些是需求中还缺的关键决策：

1. 首个 MVP 是否只做本地单用户系统？
2. 是否优先支持中国市场？
3. 初始资金、现金币种、多币种换汇是否第一版需要？
4. 是否允许融资融券、做空、杠杆？
5. 策略运行是否需要沙箱隔离？
6. 回测频率第一版是否限定日频？
7. UI 形态是 CLI、Web、本地桌面，还是先 API 后 UI？
8. 数据版权和商用边界如何处理？
9. 是否需要账户级税费、分红、送转、配股、基金分红再投？
10. 回测结果是否需要多人共享和权限管理？

## 15. 推荐第一版边界

建议第一版不要做：
- 高频或分钟级撮合。
- 期货全规则。
- Web3 链上数据。
- 自动实盘交易。
- 自然语言策略直接执行。
- 大规模参数优化。

建议第一版一定做：
- 日频事件驱动。
- checkpoint。
- 多策略分段。
- 策略版本不可变。
- 涨跌停/停牌。
- 手续费 snapshot。
- 数据版本记录。
- 基本面 point-in-time。
- 完整导入导出。

## 16. 参考资料

- AKShare: https://github.com/akfamily/akshare
- Tushare Pro 文档: https://tushare.pro/document/1?doc_id=40
- CCXT Manual: https://github.com/ccxt/ccxt/wiki/manual
- VectorBT 文档: https://vectorbt.dev/
- Backtesting.py 文档: https://kernc.github.io/backtesting.py/
- Backtrader 文档: https://www.backtrader.com/
- QuantConnect LEAN 文档: https://www.quantconnect.com/docs/v2/lean-engine
- vn.py / VeighNa: https://www.vnpy.com/
