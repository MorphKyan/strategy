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
4. 企业行为在平台内显式建模：拆分在 `split_date` 调整持仓数量和成本，现金分红在 `ex_date` 记入 `dividend_receivables`，在 `payment_date` 转入现金。
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
- 平台市场数据同步入口。

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

失败或 research-only 策略不应继续注册在 `BUILTIN_STRATEGIES` 中。

## 常用入口

从仓库根目录运行：

```powershell
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\baseline_r1_domestic_rolling.yaml --start-date 2019-02-28 --end-date 2025-06-30
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\baseline_r1_domestic_rolling.yaml --start-date 2019-02-28 --end-date 2025-06-30
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\baseline_r1_domestic_rolling.yaml --end-date 2025-06-30
.\env\python.exe platform\scripts\sync_platform_data.py --config configs\baseline_r1_domestic_rolling.yaml
.\env\python.exe platform\scripts\sync_all_market_data.py
.\env\python.exe platform\scripts\get_common_date_range.py --config platform\configs\baseline_r1_domestic_rolling.yaml
.\env\python.exe platform\scripts\run_sim_portfolio.py --config configs\baseline_r1_domestic_rolling.yaml --checkpoint <checkpoint.json> --asof-date <YYYY-MM-DD>
```

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
