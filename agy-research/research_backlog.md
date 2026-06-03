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
| R001 | 基于 Ledoit-Wolf 协方差收缩的风险平价策略 | b5bb6276-3d02-4006-8adb-9ec7f8dffb94 | 2026-06-03 15:03 | 夏普1.48 / 回撤-3.04% / 交易次数15次 | 较普通风险平价夏普提升0.026，最大回撤收缩0.29%；较EWMA夏普提升0.090，回撤收缩0.84%，且换手率大幅优化。强烈推荐采用。 | [中文实验报告](file:///D:/strategy/platform/reports/R001_Ledoit_Wolf_Covariance_Shrinkage_Risk_Parity_Report.md) |
| R002 | 基于换手率惩罚的动态再平衡控制策略 | 4d782315-f6c9-4a95-ad8f-2b1ec02f35df | 2026-06-03 13:00 | Sharpe: N/A; MaxDD: -4.66%; 换手降低 9%~31% | 换手惩罚策略在 EWMA 下可极具效用降低 31% 换手，效果显著，强烈推荐合入。 | [实验报告](file:///D:/strategy/platform/reports/experiments/risk_parity_turnover_constrained/20260603_130000/experiment_report.md) |
| R003 | 结合趋势动量与波动率靶向的动态风险预算策略 | cba2b902-6559-4259-b83d-d0746fdc3bd4 | 2026-06-03 13:10 | Sharpe 0.51->1.08, MDD -23.1%->-10.1% (MVP); Sharpe 1.67->1.62, 换手 44.9%->44.6% (RP) | 动量控制避免“越跌越买”，波动率靶向压缩回撤超50%，夏普翻倍。强烈推荐合入主干并固化推广。 | [实验报告](file:///D:/strategy/platform/reports/R003_dynamic_risk_budget_report.md) |

---

## 4. 废弃/失败的研究记录 (Failed / Deprecated)
| 任务ID | 研究课题方向 | 领用子Agent ID | 失败原因/表现衰退详情 |
| :--- | :--- | :--- | :--- |
| - | 暂无 | - | - |

---
> [!NOTE]
> **开发规约提醒**：
> 1. `TopicExplorer` 负责扫描学术界及互联网研报，往 **#2. 候选研究队列** 追加新课题。
> 2. `QuantResearcher` 启动时须将课题从 **#2** 移入 **#1** 并填入其 Conversation ID 锁定任务。
> 3. 研究结束后，子 Agent 须生成中文实验报告，并将结果总结至 **#3** 或 **#4** 中。