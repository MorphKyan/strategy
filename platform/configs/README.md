# 配置目录约定

两个子系统统一采用以下结构，各自独立维护：

| 用途 | 相对子系统根目录的位置 | 保留规则 |
| --- | --- | --- |
| 正式可复用输入 | `configs/` | 进入 Git；平台配置使用单一 `strategy`，不固定起止日期 |
| 临时生成配置 | `results/configs/<课题键>/<运行ID>/` | 不进入 Git；完成报告且实际验证可重建后清理 |
| 历史报告必需输入 | `reports/<课题键>/<版本>/configs/` | 缺少生成入口时原样保全，须标注完整复现未验证 |

`analyze_es_robustness.py` 默认生成到 `results/configs/es_robustness/<运行ID>/`。`--generated-config-dir` 接收课题目录，工具再追加运行 ID；同一次运行不得覆盖既有配置。报告附件和临时生成配置均不会自动成为正式配置，其回测结果使用临时结果目录。

## 2026-11-01 历史配置整理

原生成目录的 31 份 YAML 已逐文件校验 SHA-256，原样随所属报告保留；没有修改策略参数、交易成本或检查点设置，没有重新运行历史研究，也没有据此新增正式配置。

| 所属报告 | 输入数 |
| --- | ---: |
| [全资产组合优化](../reports/multi_asset_portfolio_optimization/20261101/report.md#配置保全与复现状态2026-11-01-整理) | 3 |
| [中国 ETF 风险平价与境外组合](../reports/china_etf_risk_parity_optimization/20261101/report.md#配置保全与复现状态2026-11-01-整理) | 9 |
| [回撤恢复实验](../reports/drawdown_recovery_experiment/20261101/report.md#配置保全与复现状态2026-11-01-整理) | 1 |
| [全球 QDII 风险平衡](../reports/global_risk_parity_qdii_backtest/20261101/report.md#配置保全与复现状态2026-11-01-整理) | 5 |
| [R038 固定权重阈值](../reports/R038_fixed_weight_threshold/20261101/report.md#配置保全与复现状态2026-11-01-整理) | 1 |
| [R060 ES 稳健性](../reports/R060_es_index_etf_robustness_analysis/20261101/report.md#配置保全与复现状态2026-11-01-整理) | 12 |

各报告列出实际输入路径与复现限制。部分其他历史报告引用的候选输入在本次整理前已经缺失，正文已注明旧命令不可直接执行；没有制造替代配置或宣称可复现。
