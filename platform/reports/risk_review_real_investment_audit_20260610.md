# 真实投资风控审查报告：策略、回测与组合产物

生成日期：2026-06-10  
审查角色：风控审查员 / reviewer  
审查范围：`platform/` 策略与回测产物、`etf_selection/` 工作流边界、现有用户持仓分析产物。  

## 结论摘要

当前系统已经具备较完整的日频事件驱动回测、交易成本、滑点、涨跌停/停牌拒单、原始价格估值、复权信号、报告和敏感性分析能力。但现有产物中存在多处不应直接用于真实投资决策的问题：

1. **部分“最优策略/最优配置”结论基于无效或过短样本**，例如 `platform/results/all_configs_evaluation_results.json` 与 `platform/results/backtest_matrix_results.json` 中大量配置实际从 `2026-01-05` 才开始，IS 指标为 0，敏感性样本数为 0。
2. **标准实验报告默认没有样本外指标**，`build_platform_metrics()` 明确写入 `oos_metrics_available=false`，但 `run_platform_experiment.py` 仍会基于全样本候选/基线差异输出“接受/继续改进”。
3. **`baseline_opt_*` 配置存在治理风险**：`screen_optimal_configs.py` 会根据训练样本 Sharpe 和敏感性标准差写入或删除 `baseline_opt_*`，但写入前未执行 `2025-07-01` 之后最终测试样本验收。
4. **报告、缓存、原始结果之间可追溯性不一致**：有些矩阵脚本会删除原始回测目录，只留下汇总 JSON/Markdown，无法复核订单、成交、拒单、现金拖累和持仓路径。
5. **用户持仓报告含实盘交易建议，但仍缺少真实账户层面的约束审查**：例如税费、申赎/停牌、基金折溢价、单日成交冲击、账户现有现金与分批执行计划。

因此，当前可以把平台作为研究与候选筛选工具使用，但在真实投资前，应把“可投策略/组合”限制为：训练样本通过、起点敏感性稳定、最终测试样本未退化、原始成交与拒单可复核、并通过人工风控会签的配置。

## 主要发现

### P0：短样本矩阵结果不应作为实盘推荐依据

证据：

- `platform/results/all_configs_evaluation_results.json` 中 26 个配置大多记录 `start_date = 2026-01-05`，`is_metrics.sharpe_ratio = 0.0`，`sensitivity_stats.count = 0`。
- `platform/results/summary_table.md` 同样显示 IS Sharpe、IS Ret、敏感性均为 0，但仍列出 Full/OOS Sharpe。
- `platform/reports/backtest_matrix_optimal_report.md` 基于这些矩阵结果推荐“最优策略”，例如 HRP 或 CVaR 动态预算。
- `platform/scripts/run_backtest_matrix.py` 运行后删除 `engine.output_dir`，导致该矩阵报告缺少可复核的 `orders.csv`、`trades.csv`、`positions.csv` 和 `manifest.json`。

影响：

- 短样本年化会极度放大近期行情，特别是 2026 年初至 2026-06-01 这类不足半年的窗口。
- IS 为 0 且敏感性样本为 0 时，不能证明训练样本稳定性。
- 删除原始结果后，无法复核成交路径、拒单、换手、现金拖累和数据质量说明。

整改建议：

- 将 `platform/reports/backtest_matrix_optimal_report.md`、`platform/results/backtest_matrix_results.json`、`platform/results/all_configs_evaluation_results.json` 标记为“研究观察/不可投”。
- 矩阵脚本必须保留原始结果或写入不可变缓存，并强制输出每个配置的真实 `start_date/end_date/observations`。
- 矩阵推荐必须先通过训练样本、起点敏感性和最终测试样本三段验证。

### P0：标准实验推荐逻辑未强制样本外验收

证据：

- `platform/src/platform_core/metrics.py` 中 `build_platform_metrics()` 固定写入 `oos_metrics_available: False`。
- `platform/src/platform_core/experiment.py` 的 `recommendation()` 只比较全样本 Sharpe、最大回撤、换手和拒单，未检查 `2025-07-01` 之后 OOS。
- 最近多份 `platform/reports/experiments/*/*/metrics.json` 的 `candidate.oos_metrics_available` 为 `false`。

影响：

- 候选策略可能在使用最终测试样本或全样本后仍被报告为“接受”。
- 对真实投资而言，这会把样本内优化误认为可外推能力。

整改建议：

- `run_platform_experiment.py` 应默认拆分 IS/OOS，并在 `metrics.json` 中写入 `is_metrics`、`oos_metrics`、`sensitivity_metrics`。
- `recommendation()` 必须在 `oos_metrics_available=true` 且 OOS 未显著退化时才允许输出“接受”。
- 对已有实验报告统一增加“是否可投”字段，默认旧报告为“不可直接投用”。

### P0：`baseline_opt_*` 配置治理不足

证据：

- `platform/configs/` 下存在 12 个 `baseline_opt_*` 配置。
- `platform/scripts/screen_optimal_configs.py` 在 `run_is_backtest_and_sensitivity()` 中把回测截断到 `2025-06-30`，随后用 `c_metrics["sharpe_ratio"] > best_sharpe + 0.02 and c_metrics["sens_std"] < 0.6` 选择候选。
- 同脚本会 `write_yaml(new_opt_path, opt_cfg_to_save)`，并可能 `unlink()` 旧的 optimal 配置；写入前没有最终测试样本阶段。

影响：

- `baseline_opt_*` 文件名容易被误解为“已验证可投最优配置”，但实际选择门槛没有覆盖 OOS。
- 脚本具有删除配置的副作用，若误运行可能破坏审计链和人工确认状态。

整改建议：

- 所有 `baseline_opt_*` 配置增加显式状态字段或旁路登记，例如 `research_status: research_only / approved / rejected`。
- 禁止筛选脚本直接删除或覆盖平台配置；改为输出候选到 `platform/reports/candidates/` 或 `etf_selection/generated_configs/`。
- 只有通过 OOS 和风控审查的配置才能进入 `platform/configs/` 顶层。

### P1：用户持仓报告含交易建议，需补充实盘执行约束

证据：

- `platform/reports/user_holdings_report.md` 基于用户持仓 `515080` 和 `563020` 输出具体买卖数量。
- 该报告覆盖 `2023-12-14` 至 `2026-06-08`，并列出 IS/OOS 和敏感性指标。
- 报告建议把大部分资产切换到 `511260`，示例中 `511260` 权重约 88% 以上。

影响：

- 组合可能形成高度债券 ETF 集中暴露，面临利率风险、流动性风险和收益上限问题。
- 报告没有充分建模真实账户的交易冲击、当日成交量占比、申赎/折溢价、税费差异、分批执行、失败订单重试和风险预算上限。
- 用户持仓标的历史较短，`563020` 从 `2023-12-14` 才有本地数据，训练样本长度较短。

整改建议：

- 用户持仓建议必须增加“不可一次性照单交易”的风控提示。
- 增加成交量占比上限、单日最大换手、资产集中度上限、目标权重漂移容忍区间和分批调仓计划。
- 对 `511260` 这类高度集中目标，额外报告利率上行冲击压力测试。

### P1：交易成本和滑点模型偏静态

证据：

- `platform/src/platform_core/execution.py` 默认 `slippage_bps=2.0`，QDII/商品默认 `6.0`。
- 买入/卖出滑点按固定 bps 加减，未随成交额、成交量、市场波动、涨跌停附近流动性动态调整。
- `FeeProfile` 只支持比例费率和最低费用。

影响：

- 对小资金和低频调仓，当前模型可能足够保守；但对用户持仓一次性大幅换仓、跨境 ETF、商品 ETF 和低流动性 ETF，固定滑点可能低估冲击成本。
- 高换手策略的真实收益可能被系统性高估。

整改建议：

- 增加基于 `amount` 的成交额占比约束和冲击成本模型。
- 报告中强制披露：最大单日成交额、成交额占当日 `amount` 比例、单资产换手峰值。
- 对 QDII/商品/黄金 ETF 单独设置压力滑点场景。

### P1：数据和报告的新鲜度需要硬门槛

证据：

- 当前本地核心 ETF 数据多数截至 `2026-06-08`，当前日期为 `2026-06-10`，尚在一周内。
- 部分历史文件如 `510050.csv`、`510180.csv` 截至 `2026-04-09`，`159980.csv` 截至 `2026-05-29`。
- 根规则要求回测时若数据与当前日期差距超过一周，应先同步数据。

影响：

- 若某配置引用了较旧数据文件，回测窗口会被截断或与其他配置不可比。
- 报告若不明确数据截止日，用户容易把旧结果当成当前结论。

整改建议：

- 每份报告必须写入所有资产的 `first_date/last_date/rows`。
- 回测入口在发现任一配置资产数据超过一周未更新时，应阻止运行或自动同步。
- 缓存必须记录数据同步时间；同步后旧缓存应标记过期。

### P2：策略实现数量较多，但缺少统一准入状态

证据：

- 当前注册策略包括 `monthly_equal_weight`、`risk_parity`、`risk_parity_ewma`、`risk_parity_lw_cov`、`hrp`、`risk_parity_cvar_dynamic_budget`、`adaptive_risk_deviation_volatility_triggered`、`cluster_representative_damped_risk_parity`、`qdii_premium_factor_rotation_risk_parity`、`risk_parity_gerber` 等。
- `platform/reports/non_baseline_research_history_summary.md` 中大量策略被标为 Failed 或物理拒绝，但注册表本身没有暴露“可投/研究中/失败”的状态。

影响：

- 只要策略在 `BUILTIN_STRATEGIES` 中注册，就可能被配置加载或被筛选脚本纳入候选。
- 研究型策略和可投策略边界不够清晰。

整改建议：

- 为每个内置策略维护元数据：`status`、`approved_configs`、`validation_report`、`risk_owner`、`last_review_date`。
- 筛选脚本默认只允许使用 `status=approved` 或显式传参启用研究策略。

## 可参考与不可投用产物清单

可参考但不可直接投用：

- `platform/reports/backtest_matrix_optimal_report.md`
- `platform/results/backtest_matrix_results.json`
- `platform/results/all_configs_evaluation_results.json`
- 未拆分 IS/OOS 的 `platform/reports/experiments/*/*/metrics.json`
- 未保留原始成交路径的矩阵汇总报告

相对更有审查价值，但仍需人工确认：

- `platform/reports/non_baseline_research_history_summary.md`
- `platform/reports/R023_Raw_Price_Reconstruction_Report.md`
- `platform/reports/R026_l2_turnover_risk_parity_report.md`
- `platform/reports/user_holdings_report.md`

## 真实投资前的最低放行清单

1. 数据：所有配置资产数据距当前日期不超过一周，并记录数据同步时间。
2. 样本：训练样本截至 `2025-06-30`，最终测试样本从 `2025-07-01` 开始。
3. 起点敏感性：从最早共同交易日起每 2 个月一组，训练样本内完成。
4. 指标：报告 IS、OOS、敏感性、换手、交易笔数、拒单、现金拖累和最大持仓集中度。
5. 成交：保留并复核 `orders.csv`、`trades.csv`、`positions.csv`、`nav.csv`、`manifest.json`。
6. 成本：至少跑默认滑点、压力滑点、单日成交额约束三套场景。
7. 治理：只有标记为 `approved` 的策略和配置可进入实盘候选池。
8. 执行：用户持仓调仓必须给出分批计划、最大单日换手、失败订单处理和停止条件。

## 总体建议

短期内，不建议把 `baseline_opt_*`、矩阵“最优策略”或用户持仓报告中的单次调仓建议直接用于真实下单。建议先建立一层“可投配置登记表”，把已通过完整验证的策略、组合、数据版本、报告路径和风控负责人固定下来；未登记的策略和配置只能作为研究观察。

