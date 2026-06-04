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
| R008 | 基于层次风险平价 (HRP) 的多资产 ETF 组合优化策略 | 490d3bd3-c217-4986-8ebf-484ef7cc8f82 | 2026-06-04 11:45 | Sharpe 1.40~1.75 -> 1.51~2.25（全线稳健提升）；MDD 全线降至约 -2% 左右；换手暴降 16% ~ 75% | 层次聚类及递归平分不需逆协方差矩阵，规避求解不稳定。回测表现夏普全线提升，回撤从 -3.5% 减至约 -2%，换手暴降平均超过 50%。物理合入主干，新增专属 yaml。 | [中文实验报告](file:///C:/Users/morph/.gemini/antigravity-cli/brain/a8507162-2a8b-4a61-a40d-a957e9897f47/.system_generated/worktrees/subagent-Quant-Researcher-R008-quant-researcher-228b44eb/platform/reports/R008_HRP_Multi_Asset_ETF_Optimization_Report.md) |
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
| R007 | 结合 DCC-GARCH 动态协方差预测与动量过滤的 ETF 轮动风险平价策略 | 5fd5d059-99c7-4bd1-8090-1f7ad766dccf | 夏普比率全线严重退化（如 LW Cov 2.67->1.40）；20日动量硬过滤导致严重的 whipsaw 顺周期磨损与踏空效应；DCC-GARCH 条件协方差估计时变噪声极大，导致年化换手率暴涨数倍。物理拒绝进入平台。 |

---
> [!NOTE]
> **开发规约提醒**：
> 1. `TopicExplorer` 负责扫描学术界及互联网研报，往 **#2. 候选研究队列** 追加新课题。
> 2. `QuantResearcher` 启动时须将课题从 **#2** 移入 **#1** 并填入其 Conversation ID 锁定任务。
> 3. 研究结束后，子 Agent 须生成中文实验报告，并将结果总结至 **#3** 或 **#4** 中。
