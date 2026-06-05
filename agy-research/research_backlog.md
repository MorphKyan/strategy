# AGY 量化研究看板 (Research Backlog)

该看板是多 Agent 协同量化研究的核心去重和状态同步机制。所有新发掘的研究方向将首先登记在此，并由各个 `QuantResearcher` 实例认领执行。

---

## 1. 正在进行中的研究 (In-Progress / Running)
| 任务ID | 研究课题方向 | 领用子Agent ID | 启动时间 | 预估完成时间 | 当前状态/最新日志 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| - | 暂无 | - | - | - | - |

---

## 2. 候选研究队列 (Todo Backlog)
| 任务ID | 研究课题方向 | 核心研究背景/期望改进 | 优先级 | 数据依赖 | 推荐回测配置 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| - | 暂无 | - | - | - | - |


---

## 3. 已完成研究历史 (Completed / Finished)
| 任务ID | 研究课题方向 | 领用子Agent ID | 结束时间 | 核心实验表现 (Sharpe/MDD/换手率) | 结论及推荐动作 | 实验报告链接 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| R019 | 基于聚类代表性与切换阻尼的渐进式 ETF 筛选与轮动风险平价策略 | a5fbf143-10d3-48b1-a422-cb50d53c163b | 2026-06-05 08:12 | 扩充6资产基准 Sharpe 1.369 -> CRD 1.736, MDD -5.41% -> -4.47%, 换手率及摩擦优化 | CRD 聚类代表性渐进筛选极其有效。双重阻尼模式有效将年化换手削减 36.8%~53.7%，平滑 whipsaw 损耗。无样本外过拟合，物理合入主干并固化 yaml。 | [中文实验报告](file:///D:/strategy/platform/reports/R019_Cluster_Representative_Damped_Rotational_Report.md) |
| R018 | 基于 Gini 均差 (Gini Mean Difference, GMD) 稳健风险度量的风险平价策略 | f8f19f51-6c9e-401f-8d7e-f34bf75e97bf | 2026-06-05 08:27 | MVP Sharpe 1.938->3.009, MDD -11.14%->-3.20%; GlobalDiv Sharpe 1.531->1.489, MDD -2.90%->-4.29%; 换手全线降15%~30% | 各配置下年化换手率全线下降 15%~30%，换手控制极其优秀。然而全球红利夏普轻微退化，且多个大类配置最大回撤恶化。判定为差异不大/局部优势，物理拒绝。 | [中文实验报告](file:///D:/strategy/platform/reports/R018_Gini_Mean_Difference_Robust_Risk_Parity_Report.md) |
| R016 | 基于自适应风险偏离阈值与系统波动触发的动态再平衡风险平价策略 | 8d6155e0-78f3-4544-a5f5-a697961b4e6b | 2026-06-04 20:10 | MVP Sharpe 1.938->2.816, MDD -11.14%->-3.58%; Nasdaq Sharpe 1.753->2.027, MDD -3.66%->-2.50% | 动态偏离自适应为策略提供优秀换手阻尼，交易笔数和换手率在各配置下录得断崖式下跌(-30%~-80%)，极好平滑 whipsaw 交易磨损。同时夏普比率在全基准配置下录得显著提升，最大回撤大幅收紧。物理合入主干并固化。 | [中文实验报告](file:///D:/strategy/platform/reports/R016_Adaptive_Risk_Deviation_Volatility_Triggered_Report.md) |
| R015 | 基于 Oracle Approximating Shrinkage (OAS) 协方差估计的风险平价策略 | f8db5acd-62c7-4d2b-a086-e0198bf29b97 | 2026-06-04 22:00 | MVP Sharpe 1.94->2.63, MDD -11.14%->-4.95%; LW Sharpe 2.67->2.65, MDD -4.51%->-4.95% | 多数多资产配置下夏普退化且最大回撤变大，且换手率增幅超30%。判定为差异不大/局部优势 (物理拒绝/未合入代码)。 | [中文实验报告](file:///D:/strategy/platform/reports/R015_OAS_Covariance_Risk_Parity_Report.md) |
| R014 | 基于中位数绝对偏差 (MAD) 稳健波动率估计 of 风险平价策略 | 55df5935-79d7-44f3-879e-395931945b0d | 2026-06-04 20:10 | 局部提升 (Nasdaq 夏普+0.20)，但多资产组合退化 (CVaR -0.23)，且 HRP 换手率剧增 74% 触发红线。 | 差异不大/有局部优势 (物理拒绝/未合入代码) | [中文实验报告](file:///D:/strategy/platform/reports/R014_MAD_Robust_Volatility_Risk_Parity_Report.md) |
| R012 | 基于 CVaR 动态预算与波动率目标控制的风险平价策略 | 0b64290c-b32c-4ea3-ac78-39f55bca0a35 | 2026-06-04 15:10 | MVP Sharpe 1.93->3.29, MDD -11.14%->-1.63%; LW Sharpe 2.66->3.27, MDD -4.51%->-1.63% | 全线测试配置下夏普显著提升，最大回撤大幅收紧，无过拟合风险且换手率合理，物理合入主干并固化。 | [中文实验报告](file:///D:/strategy/platform/reports/R012_CVaR_Dynamic_Budget_Volatility_Target_Report.md) |
| R011 | 基于下行半协方差的稳健风险平价策略 | a2e8c45f-e772-4e20-b0f6-9116c2bdae6e | 2026-06-04 15:05 | Sharpe 局部有提升（如MVP +0.55），但在国内滚动及大部分 EWMA 多资产组合中下降（如 low_vol -0.05, global_dividend -0.16），且换手率多处增幅超 30%（最高+118%） | 仅特定资产包有效且表现平庸，部分组合换手率大幅升高触发交易摩擦红线，判定为局部优势，已根据规约物理拒绝进入 platform 主干，策略代码完全擦除。 | [中文实验报告](file:///D:/strategy/platform/reports/R011_Downside_Semi_Covariance_Risk_Parity_Report.md) |
| R008 | 基于层次风险平价 (HRP) 的多资产 ETF 组合优化策略 | 490d3bd3-c217-4986-8ebf-484ef7cc8f82 | 2026-06-04 11:45 | Sharpe 1.40~1.75 -> 1.51~2.25（全线稳健提升）；MDD 全线降至约 -2% 左右；换手暴降 16% ~ 75% | 层次聚类及递归平分不需逆协方差矩阵，规避求解不稳定。回测表现夏普全线提升，回撤从 -3.5% 减至约 -2%，换手暴降平均超过 50%。物理合入主干，新增专属 yaml。 | [中文实验报告](file:///D:/strategy/platform/reports/R008_HRP_Multi_Asset_ETF_Optimization_Report.md) |
| R009 | 基于 SCRIP 算法的带 L1 换手率约束的风险平价优化策略 | 6d31bfc7-20ca-4300-9be6-f1c8bf24a9e8 | 2026-06-04 11:55 | Sharpe 在国内组合中改善明显（LW Cov +0.09, EqualWeight +0.78），但全球境外组合退化严重（美股混合 -0.31）；最大回撤国内收缩明显（EqualWeight -11.1%->-3.88%） | 换手控制极佳，国内改善明显但境外严重踏空退化。判定为差异不大/局部优势，已物理拒绝合入 platform 主干。 | [中文实验报告](file:///D:/strategy/platform/reports/R009_SCRIP_L1_Turnover_Constraint_Risk_Parity_Report.md) |
| R010 | 基于 Yang-Zhang 极差波动率与收缩协方差的稳健风险平价策略 | 3c928b80-fdb1-4e94-842d-38655b103b50 | 2026-06-04 12:00 | MVP夏普1.938->2.755，Nasdaq夏普1.753->1.993；但在全球 EWMA、美股混合及国内低波夏普微降 | 判定为差异不大/局部优势。未能通过全线配置夏普提升的要求，已根据规约物理拒绝合入 platform 主干，并清除全部代码。 | [中文实验报告](file:///D:/strategy/platform/reports/R010_Robust_Risk_Parity_Yang_Zhang_Covariance_Report.md) |
| R006 | 基于随机矩阵理论 (RMT) 特征值清洗的协方差风险平价策略 | fe9f14b4-df8a-41ab-a3c4-de618206168c | 2026-06-04 11:20 | Sharpe: 局部改善（MVP +0.77, 国内滚动 +0.08），但 EWMA 略有变差；换手率局部暴增（最高+66.35%） | 换手率增幅超30%，未通过过拟合审计；在部分配置下夏普略有下降。判定为差异不大/局部优势，已物理拒绝合入 platform 主干。 | [中文实验报告](file:///C:/Users/morph/.gemini/antigravity-cli/brain/6d9cb386-c516-4c86-855d-dcb410e441f7/.system_generated/worktrees/subagent-Quant-Researcher---R006-quant-researcher-431ca5f0/platform/reports/R006_RMT_Clean_Covariance_Risk_Parity_Report.md) |
| R004 | 基于 GARCH(1,1) 与下行半方差的非对称风险平价策略 | 6d919fb5-71fa-47db-b56b-629da99e0e48 | 2026-06-03 23:20 | Sharpe 1.40->1.45(Roll)/2.67->2.99(LW); MaxDD -4.5%->-3.8%; 换手率微增 | 新策略有效提升组合夏普比率并缩减最大回撤。换手率微增，强烈推荐作为高性能波动防御配置合入主干并固化。 | [中文实验报告](file:///D:/strategy/platform/reports/R004_Asymmetric_Risk_Parity_Garch_Semi_Variance_Report.md) |
| R001 | 基于 Ledoit-Wolf 协方差收缩的风险平价策略 | b5bb6276-3d02-4006-8adb-9ec7f8dffb94 | 2026-06-03 15:48 | Sharpe 1.49(MVP)/1.61(GlobEWMA); MaxDD -3.04%/-3.45%; 换手暴降30%~50% | 全基线重跑验证，多资产下夏普大幅提升，最大回撤收缩，换手和调仓频率暴减，强烈推荐作为缺省算法。 | [中文实验报告](file:///D:/strategy/platform/reports/R001_Ledoit_Wolf_Covariance_Shrinkage_Risk_Parity_Report.md) |
| R002 | 基于换手率惩罚的动态再平衡控制策略 | c4f38532-ef71-43df-b424-7bae666071c4 | 2026-06-03 16:15 | Sharpe 1.25~2.10 vs 1.36~1.77 | 较普通风险平价换手降低10%~30%，但在强趋势组合中滞后显著，且表现全面逊于LW协方差收缩。作为可选策略保留，不修改基准配置文件。 | [重新评估报告](file:///D:/strategy/platform/reports/R002_re_run_report.md) |
| R003 | 结合趋势动量与波动率靶向的动态风险预算策略 | 180ede3e-f891-4a93-ad70-700ddf692fc1 | 2026-06-03 16:25 | Sharpe 1.94->2.17, MDD -11.1%->-4.5% (MVP/窄配置); Sharpe 1.40~1.71 vs 1.07~1.54 | 窄资产池防御极佳，但在大涨趋势的多资产组合中，因固定波动率目标造成踏空，整体夏普逊于LW协方差收缩。不修改默认配置，保留为备选策略类。 | [重新评估报告](file:///D:/strategy/platform/reports/R003_re_run_report.md) |
| R005 | 引入黑天鹅防范与极端风险度量的 CVaR 风险平价策略 | b1e3e2d1-2243-468f-a524-ea9e14c5117d | 2026-06-03 23:16 | Sharpe 2.81(MVP)/2.80(LW_Cov) vs 1.94/2.67; MDD -2.72% vs -11.14%/-4.51%; 换手率上升 | 局部优势极其显著（防守防黑天鹅效果佳，夏普提升，回撤骤降）；但在 EWMA 中因小样本估值噪声有过度交易。作为可选备选策略保留，不修改 defaults yaml。 | [中文实验报告](file:///D:/strategy/platform/reports/R005_CVaR_Risk_Parity_Report.md) |

---

## 4. 废弃/失败的研究记录 (Failed / Deprecated)
| 任务ID | 研究课题方向 | 领用子Agent ID | 失败原因/表现衰退详情 |
| :--- | :--- | :--- | :--- |
| R017 | 基于单变量 GARCH 与 Ledoit-Wolf 收缩相关系数的混合协方差风险平价策略 | de1c5e7a-eba1-4230-ac51-4660aef0884b | 在部分大类配置（全球红利/EWMA）上表现退化，且由于 GARCH 条件标准差的时变敏感性，在各配置下的年化换手暴涨（最高+243.9%）严重触发 30% 限制红线，存在严重过拟合与摩擦损耗，物理拒绝并完全清除代码。 |
| R007 | 结合 DCC-GARCH 动态协方差预测与动量过滤的 ETF 轮动风险平价策略 | 5fd5d059-99c7-4bd1-8090-1f7ad766dccf | 夏普比率全线严重退化（如 LW Cov 2.67->1.40）；20日动量硬过滤导致严重的 whipsaw 顺周期磨损与踏空效应；DCC-GARCH 条件协方差估计时变噪声极大，导致年化换手率暴涨数倍。物理拒绝进入平台。 |
| R013 | 基于 etf_selection 多维打分筛选的 ETF 轮动风险平价策略 | 26e24bd9-411a-4471-aa79-fc097db1b7c7 | 夏普比率全线表现退化（大部分配置夏普降至0.439）；在 12-ETF 袖子扩充宇宙中，得分轮动使得夏普比率由 0.974 恶化至 0.554，年化换手率暴增 296.40%，存在严重 whipsaw 磨损与过拟合风险。已物理清除策略代码，物理拒绝合入平台。 |

---
> [!NOTE]
> **开发规约提醒**：
> 1. `TopicExplorer` 负责扫描学术界及互联网研报，往 **#2. 候选研究队列** 追加新课题。
> 2. `QuantResearcher` 启动时须将课题从 **#2** 移入 **#1** 并填入其 Conversation ID 锁定任务。
> 3. 研究结束后，子 Agent 须生成中文实验报告，并将结果总结至 **#3** 或 **#4** 中。
