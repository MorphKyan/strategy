# R049 椭球稳健自适应在线组合选择（RELP-Adap）研究笔记

## 基本信息

- 研究 ID：R049
- Owner：`/root`
- 创建时间：2026-07-11 Asia/Shanghai
- 状态：`Failed`
- 关联看板项：`research-dashboard/research_backlog.md`

## 假设、来源与反证风险

- 假设：论文的椭球鲁棒单期预测、显式比例成本约束、`L1` 换手惩罚与顺序专家选择可在固定四只中国真实 ETF 上抑制 OLPS 过度交易。
- 来源：Tsang、Sit、Wong，*Adaptive robust online portfolio selection*，EJOR 321(1), 214–230 (2025)，DOI `10.1016/j.ejor.2024.09.002`；已逐项读取作者公开 TeX（`arXiv:2206.01064`）。
- 主要风险：连续成本预算与平台实际扣费不同；`m+1=5` 协方差可能病态；专家切换会被整手、最低费用和滞后执行破坏。

## 阶段 A 公式映射与预注册

- `x_t = p_t / p_{t-1}`；moving-average-reversion 预测为 `x_tilde = mean(p[t-W+1:t]) / p[t]`，`W=5`。
- `Sigma` 是最近 `m+1=5` 个共同 price relatives 的样本协方差，`Sigma=U' U`；椭球集合为 `(x-x_tilde)' Sigma^-1 (x-x_tilde) <= kappa^2`。
- Theorem 5 SOCP：最大化 `b' x_tilde - lambda * ||b_hat_prev-b||_1 - kappa * ||U b||_2`，约束 `1'b + gamma * ||b_hat_prev-b||_1 <= 1`、`b >= 0`；目标输出归一化为 `b/(1'b)`，缩放损失只作模型成本诊断，平台仍按真实费用和滑点记账。
- 等价条件为 `max(x_tilde) > kappa * sigma + lambda`；不成立、非最优或残差超限时保持上一实际漂移权重，并记录 `solver_failure`。
- 唯一 adaptive 版本冻结为论文 `RELP-Adap-1`：`lambda` 与 `kappa` 均用 SB expert scheme，`z=1.96`、`delta=0`、选择窗口 `W=5`。专家为 25 个 `(kappa, lambda)` 组合：`kappa={0.1,0.31622777,1,3.16227766,10}`，`lambda=10*gamma*{0.1,0.31622777,1,3.16227766,10}`。
- 决策频率冻结为每 5 个共同交易日；资产固定为四只真实 ETF、初始各 25%；`gamma=0.0002` 仅映射平台费率，不在 NAV 中二次扣费。
- 时序：只使用 `context.date` 前的共同交易日；目标至少滞后一根 bar 执行；专家财富只在当期已实现相对价格后更新。
- 求解器：`cvxpy==1.7.5`，`CLARABEL` 优先、`SCS` 仅数值复核，容差 `1e-8`、约束残差上限 `1e-6`。

## 样本与禁止事后修改

- 训练截至 `2025-06-30`；最终测试从 `2025-07-01` 起，只在完整冻结后运行。
- 数据审计（2026-07-11）：四标的无重复日期、`close` 与 `amount` 无缺失；共同交易区间为 `2019-01-18` 至 `2026-07-10`，共 1,810 日，其中训练期 1,560 日。最新日期距运行日 1 天，满足新鲜度和三年共同历史门槛。
- 数值等价冒烟测试：在二维正定协方差样例中，`CLARABEL` 返回 `optimal`，SOCP 目标 `1.0078865027`、解 `[0.999808038, 0]`、成本约束残差小于 `1e-9`，且 Theorem 5 的充分条件成立。
- 禁止在最终测试后修改公式、adaptive 版本、专家集合、频率、lag、成本映射、求解器/容差、资产或验收阈值。
- 阶段 A 未通过将停止，不读取最终测试样本。

## 训练验证与结论

- 阶段 A 的二维 SOCP/no-trade/JSON checkpoint 序列化测试通过；首次训练运行发现 `date` 不能序列化，改为 ISO 日期后重跑，未改变任何冻结参数。
- 训练命令：`.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\r049_robust_ellipsoidal_online_portfolio_adaptive.yaml --baseline-config configs\r8_permanent_real_fixed_weight_threshold.yaml --experiment-name r049_training_vs_fixed_weight --start-date 2019-01-18 --end-date 2025-06-30 --no-charts --slippage-scenario all`。
- 三个场景的候选 Sharpe 为 `0.0868`、`-0.2299`、`-0.2379`，主基线为 `1.1715`、`1.1682`、`1.1643`；候选年化换手为 `19.7465`、`19.7750`、`19.5461`，主基线为 `0.1024`、`0.1025`、`0.0997`。候选交易数为 `410/420/418`，主基线均为 `24`。
- 三滑点下 Sharpe、收益和最大回撤同时显著退化，且换手与订单数违反预冻结硬门槛。因此停止研究；不运行机制基线、起点敏感性或最终测试，且不读取 `2025-07-01` 之后结果。
- 候选策略源码、注册、配置和测试已清理；原始 artifacts 与标准化报告保留。详见 `platform/reports/r049_relp_adap_failed_report.md`。
