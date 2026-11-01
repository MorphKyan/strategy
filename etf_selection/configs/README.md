# 配置目录约定

目录结构与 platform 一致，文件仍由本子系统独立维护：

| 用途 | 相对子系统根目录的位置 | 保留规则 |
| --- | --- | --- |
| 正式可复用输入 | `configs/` | 进入 Git；包含 ETF 候选池与筛选参数 |
| 临时生成配置 | `results/configs/<课题键>/<运行ID>/` | 不进入 Git；完成报告且实际验证可重建后清理 |
| 历史报告必需输入 | `reports/<课题键>/<版本>/configs/` | 缺少生成入口时原样保全，须标注完整复现未验证 |

正式输入为 `etf_universe.yaml` 和 `etf_universe_style_cross_market.yaml`。`paths.generated_config_dir` 指定包含课题键的输出根目录，筛选入口追加运行 ID；两份配置分别使用 `etf_sleeves`、`style_cross_market` 课题。自动摘要和明细写入 `results/screening/<运行ID>/`，正式报告按根目录约定发布。

## 2026-11-01 历史配置整理

- 52 份历史 YAML 已逐文件校验 SHA-256 后保全，仅更新 16 份对照配置中的路径引用，策略与执行参数不变：[执行优化报告](../reports/platform_execution_validation/20260531/report.md)保留 32 份候选、旧执行对照及优化执行对照；[ETF 袖子报告](../reports/etf_sleeves/20260531/report.md)保留 20 份候选。
- 32 份重复配置在确认保留副本逐字节一致后删除。
- 7 份混放的筛选明细和执行记录移到 `results/screening/<原运行ID>/`；未重新计算、覆盖已有结果或更改历史指标。
- 历史平台输入使用 `strategies.segments`，当前引擎要求单一 `strategy`，不能直接运行。保留原格式便于核实原版本，完整复现尚未验证。

## 尚待核验的临时输入

以下 23 份 YAML 尚未确认正式报告归属或可重建性，因此保留于临时目录，没有删除或升级为正式配置。恢复研究时，先确认原代码、依赖与数据快照，再补齐复现入口；旧版回测配置须显式迁移。

| 临时目录 | YAML 数 | 待核验内容 |
| --- | ---: | --- |
| `results/configs/style_cross_market/20260531_012414_style_cross_market_platform/` | 12 | 风格及跨市场候选、同窗口对照 |
| `results/configs/style_cross_market/20260531_013145_style_cross_market_refine_platform/` | 8 | 风格细化候选、同窗口对照 |
| `results/configs/style_cross_market/20260531_data_sync/` | 1 | 旧行情同步输入，不是回测配置 |
| `results/configs/etf_sleeves/20260531_111355/` | 2 | 三资产候选 |

这些本机临时文件不进入 Git；本说明不将其视为永久归档或已经验证的复现入口。
