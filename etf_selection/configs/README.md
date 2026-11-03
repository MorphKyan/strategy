# 配置目录约定

本子系统独立维护筛选输入，目录结构与 platform 一致。

| 用途 | 相对子系统根目录的位置 | 保留规则 |
| --- | --- | --- |
| 正式可复用输入 | `configs/` | 进入 Git，包含候选池与筛选参数。 |
| 临时生成配置 | `results/configs/<课题键>/<运行ID>/` | 不进入 Git；完成报告且实际验证可重建后清理。 |
| 历史报告必需输入 | `reports/<课题键>/<版本>/configs/` | 缺少生成入口时保全，明确复现限制。 |

正式输入为 `etf_universe.yaml` 和 `etf_universe_style_cross_market.yaml`，分别对应 `etf_sleeves` 和 `style_cross_market` 课题。`paths.generated_config_dir` 指定课题输出根目录，筛选入口追加运行 ID。自动摘要和明细写入 `results/screening/<运行ID>/`。

历史候选和执行对照见 [ETF 袖子报告](../reports/etf_sleeves/20260531/report.md)及[平台执行验证报告](../reports/platform_execution_validation/20260531/report.md)。保留附件不代表完整复现已验证；旧 `strategies.segments` 格式须显式迁移后才能交给当前引擎。不同费用、资产和窗口的配置不混并。
