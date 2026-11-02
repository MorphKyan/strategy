# 运行产物目录

| 目录 | 用途 |
| --- | --- |
| `backtests/` | 正式固定配置的完整共同历史运行。 |
| `temporary_backtests/direct/` | 临时直接运行及固定历史窗口研究。 |
| `temporary_backtests/experiments/` | 候选、基线及成本场景实验。 |
| `temporary_backtests/legacy_unclassified/` | 来源不能证明为正式完整历史的旧运行。 |
| `sensitivity/` | 起点敏感性数据、检查点、汇总和配图。 |
| `configs/` | 运行时生成的研究配置。 |
| `live_portfolios/`、`live_rebuilds/`、`sim_portfolios/` | 账户与恢复状态。 |
| `live_reports/` | 实盘展示和归因输出。 |

默认看板只读取符合来源要求的 `backtests/`，开启全局选项可包含临时回测；敏感性不进入看板。

旧运行快照保留当时的配置内容，不直接作为正式配置使用。中间产物在课题报告完成、实际验证可重建后清理；行情、账户和恢复检查点独立保护。最终研究报告与复现入口位于 `reports/`。
