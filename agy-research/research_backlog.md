# AGY 量化研究看板 (Research Backlog)

该看板是多 Agent 协同量化研究的核心去重和状态同步机制。所有新发掘的研究方向将首先登记在此，并由各个 `QuantResearcher` 实例认领执行。

---

## 1. 正在进行中的研究 (In-Progress / Running)
| 任务ID | 研究课题方向 | 领用子Agent ID | 启动时间 | 预估完成时间 | 当前状态/最新日志 |
| :--- | :--- | :--- | :--- | :--- | :--- |

---

## 2. 候选研究队列 (Todo Backlog)
| 任务ID | 研究课题方向 | 核心研究背景/期望改进 | 优先级 | 数据依赖 | 推荐回测配置 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| R002 | 基于换手率惩罚的动态再平衡控制策略 | 硬性阈值再平衡容易在临界点频繁交易或产生巨大单次冲击成本，引入换手率的 L1 惩罚或硬性上限约束，可实现更平滑的阻尼渐进式调仓。 | Medium | 现有 ETF 历史日线数据 | 策略：`risk_parity_turnover_constrained`，参数：`turnover_penalty_lambda=0.01/0.05` |
| R003 | 结合趋势动量与波动率靶向的动态风险预算策略 | 传统等风险预算在资产下行周期中容易“越跌越买”，引入 Sleeve 级别的趋势动量动态调节风险预算，并利用波动率靶向控制大底回撤。 | High | 现有 ETF 历史日线数据 / sleeves 结构 | 策略：`risk_parity_dynamic_budget`，参数：`momentum_window=60`, `momentum_sensitivity=1.5`, `volatility_target=0.08` |

---

## 3. 已完成研究历史 (Completed / Finished)
| 任务ID | 研究课题方向 | 领用子Agent ID | 结束时间 | 核心实验表现 (Sharpe/MDD/换手率) | 结论及推荐动作 | 实验报告链接 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| R001 | 基于 Ledoit-Wolf 协方差收缩的风险平价策略 | 9f214c7b-08ff-47bb-82ec-10371f0b0bc7 | 2026-06-03 11:00 | Sharpe: 1.6775 (vs 1.6685), MDD: -4.37%, 年化换手率: 44.82% (vs 44.93%) | Sharpe提升，波动率和换手降低，推荐合并 | [实验报告](file:///C:/Users/morph/.gemini/antigravity-cli/brain/419e7723-6b9d-45aa-a98c-cfd5ad22f4bd/.system_generated/worktrees/subagent-Quant-Researcher--R001--quant-researcher-5cc36bdb/platform/reports/R001_risk_parity_lw_cov_report.md) |

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
