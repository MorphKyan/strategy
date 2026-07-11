# R047 Wasserstein 分布稳健对数增长全天候组合：数据与数值可行性审计

**结论：`Failed`（数据门槛与依赖均通过；训练主对照否证候选，未运行最终测试）。**

## 假设与方法边界

R047 预注册目标是在真实 ETF 的 long-only、现金与集中度约束下，最大化 Wasserstein 模糊分布中的最坏情形期望对数增长，并将交易成本显式纳入目标或约束。该目标不能替换为均值—方差、风险平价、逆波动率、等权或网格启发式。

Hsieh 与 Yu 的研究将收益分布歧义表述为 Wasserstein 距离，并在一般凸交易成本下借助对偶理论把无限维问题近似为有限凸规划；其成本敏感实证也显示，交易成本会使配置向无风险资产偏移。[On Cost-Sensitive Distributionally Robust Log-Optimal Portfolio](https://arxiv.org/abs/2410.23536) Costa 与 Kwon 的工作同样强调分布稳健问题需要在模糊集中求对抗性分布，并采用投影梯度与序贯凸规划求解；该文只作为“最坏分布”数值求解的参考，不用于把 R047 改写成风险平价。[Data-driven distributionally robust risk parity portfolio optimization](https://arxiv.org/abs/2110.06464)

## 数据审计

审计日为 `2026-07-11`；本地 CSV 最后交易日均为 `2026-07-10`，距离审计日 1 个日历日，满足 7 日新鲜度规则。检查对象为 `510300`、`512890`、`513100`、`518880`、`511260`、`159985`、`159981`，没有使用 `511260_3X`。

| 检查项 | 结果 |
| --- | --- |
| 共同可用日期 | `2020-01-17` 至 `2026-07-10`，1,566 个共同交易日 |
| 训练共同日期 | 至 `2025-06-30` 共 1,316 个交易日，超过 3 年 |
| 每个标的的重复日期 | 0 |
| 每个标的的非正或缺失 `amount` | 0 |
| 每个标的的非正 OHLC / `adjust_factor` | 0 |
| 数据源与更新时间 | CSV 内为 `finshare`；各文件 `updated_at` 为 `2026-07-10` |

此审计仅检查数据日期和字段质量；没有读取、计算或比较 `2025-07-01` 之后的策略绩效。

## 数值可行性审计

当前项目解释器为 `env\\python.exe`；依赖探测结果如下。依赖安装已获用户授权，因此缺失的正常计算依赖必须以版本锁定方式补足，而不能作为失败理由；仍不得把启发式权重冒充 Wasserstein 稳健解。

| 依赖 | 可用性 | 对 R047 的影响 |
| --- | --- | --- |
| `numpy` | 可用 | 只能提供数组运算，不提供约束凸优化器。 |
| `scipy` | 已安装 `1.15.3` | 数值辅助。 |
| `cvxpy` | 已安装 `1.7.5` | 表达和求解有限维凸规划及其对偶约束。 |
| `POT` / Wasserstein 工具 | 未安装 | 仅在公式实现确有需要时安装并锁定。 |
| `sklearn` | 不可用 | 无可复用的稳健性/重采样辅助设施；这不是单独阻断项。 |

手写一个求解器、临时引入未经锁定的新依赖，或以候选权重网格近似最坏情形，都会改变预注册求解方法或制造无法审计的数值误差。R047 还要求半径由训练样本 block bootstrap 置信规则或可复现解析规则确定，而非按 Sharpe 搜索；安装后须先完成公式到约束的映射和独立数值验证。

## 继续研究的前置条件

尚未新增 `Strategy.generate_targets(context)` 实现、注册策略或平台配置，也未执行训练主对照、起点敏感性或最终测试；故当前不存在 Sharpe、收益、回撤、换手、交易、订单、拒单、现金权重或执行滑点指标。

在不接触最终测试绩效前，先安装并锁定凸优化依赖，提供可复现的 Wasserstein 半径规则、文献公式至代码约束的逐项映射，以及独立的数值可行性/最优性测试；然后继续执行完整三滑点训练与自然月起点敏感性。不得用替代目标继续回测。

已执行 `cvxpy` 最小对数目标求解自检：`cvxpy==1.7.5`、`scipy==1.15.3`，可用求解器为 `CLARABEL`、`OSQP`、`SCIPY`、`SCS`，`CLARABEL` 返回 `optimal`。先前安装的 yanked `cvxpy==1.7.0` 已立即替换，不作为冻结版本。

## 审计命令

```powershell
.\env\python.exe -
.\env\python.exe -m pip install "scipy==1.15.3" "cvxpy==1.7.5"
```

该命令读取七个 `platform/data/<code>.csv` 的日期、OHLC、`amount`、`adjust_factor` 字段并探测求解依赖；没有调用回测入口。

## 训练主对照（2026-07-11）

候选在读取任何最终测试绩效前完成参数冻结：126 个交易日回看、5 日收益情景、至少 24 个情景、3 情景移动块 bootstrap、32 次重抽样、95% 分位半径、固定种子 `47047`、单资产上限 `35%`、`objective_cost_rate=0.0008`、`minimum_wealth=0.2`、月末决策。首个 252 日/64 次实现因逐条构建对偶约束在 120 秒内超时，未生成可用指标；随后在未读取任何回测绩效前将相同目标和约束向量化，并冻结为上述可在平台中完成的规模。

实现的是离散经验情景上 1-Wasserstein 球的运输问题对偶：对每个源情景 `i` 与目标情景 `j`，约束为 `alpha_i <= log(1 + r_j^T w - c||w-w_prev||_1) + lambda*d_ij`，并最大化 `mean(alpha)-lambda*epsilon`。这与 Wasserstein-DRO 的有限凸重构路径一致；相关理论说明经验分布 Wasserstein 球可重构为有限凸规划，并可由置信半径控制样本误差。[Mohajerin Esfahani 与 Kuhn](https://arxiv.org/abs/1505.05116)

训练窗口为 `2020-01-17` 至 `2025-06-30`。以下指标直接由各 raw artifact 的 `nav.csv`、`trades.csv`、`orders.csv`、`skipped_orders.csv`、`positions.csv` 生成并写入相同目录的 `metrics.json`。

| 滑点 | 策略 | annualized_return | sharpe_ratio | max_drawdown | annualized_turnover | trade_count / order_count / rejected_order_count | average_cash_weight | execution_slippage |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| default | 候选 | 0.00% | 0.0000 | 0.00% | 0.00% | 0 / 0 / 0 | 100.00% | 0.0000% |
| default | monthly_equal_weight | 11.73% | 1.1731 | -9.51% | 27.61% | 389 / 389 / 0 | 0.24% | 0.0449% |
| default | risk_parity_lw_cov | 7.09% | 1.9398 | -2.59% | 25.95% | 367 / 367 / 0 | 9.43% | 0.0352% |
| stress | 候选 | 0.00% | 0.0000 | 0.00% | 0.00% | 0 / 0 / 0 | 100.00% | 0.0000% |
| stress | monthly_equal_weight | 11.60% | 1.1601 | -9.51% | 27.81% | 384 / 384 / 0 | 0.26% | 0.2239% |
| stress | risk_parity_lw_cov | 7.00% | 1.9188 | -2.56% | 25.75% | 362 / 362 / 0 | 9.46% | 0.1755% |
| dynamic_participation | 候选 | 0.00% | 0.0000 | 0.00% | 0.00% | 0 / 0 / 0 | 100.00% | 0.0000% |
| dynamic_participation | monthly_equal_weight | 11.70% | 1.1696 | -9.51% | 27.53% | 381 / 381 / 0 | 0.25% | 0.0716% |
| dynamic_participation | risk_parity_lw_cov | 7.09% | 1.9392 | -2.59% | 25.94% | 366 / 366 / 0 | 9.43% | 0.0389% |

## 判定

**最终结论：`Failed`。** 候选的所有月度求解均返回现金解，平均现金权重为 `100%`，没有成交；相对三种滑点下较优的 `risk_parity_lw_cov`，Sharpe 差为 `-1.9398`、`-1.9188`、`-1.9392`，并且年化收益低约 7 个百分点。虽然最大回撤为零，但这是长期空仓而非可接受的风险调整改善，直接违反预冻结的平均现金权重不超过 40% 和 Sharpe 容忍门槛。

因此不运行日历起点敏感性、冻结或 `2025-07-01` 起最终测试。候选策略源码、注册与 R047 专用配置已清理；原始 artifacts 和本报告保留。依赖安装不构成失败原因。

训练命令：

```powershell
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\r047_wasserstein_robust_log_growth.yaml --start-date 2020-01-17 --end-date 2025-06-30
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\r047_monthly_equal_weight.yaml --start-date 2020-01-17 --end-date 2025-06-30
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\r047_risk_parity_lw_cov.yaml --start-date 2020-01-17 --end-date 2025-06-30
```

主要 raw artifact：

- `platform/results/backtests/r047_wasserstein_robust_log_growth_{default,stress,dynamic_participation}_20260711_*`
- `platform/results/backtests/r047_monthly_equal_weight_{default,stress,dynamic_participation}_20260711_*`
- `platform/results/backtests/r047_risk_parity_lw_cov_{default,stress,dynamic_participation}_20260711_*`
