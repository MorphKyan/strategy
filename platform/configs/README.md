# 配置目录约定

| 用途 | 相对子系统根目录的位置 | 保留规则 |
| --- | --- | --- |
| 正式可复用输入 | `configs/` | 进入 Git；单一 `strategy`，不固定起止日期。 |
| 临时生成配置 | `results/configs/<课题键>/<运行ID>/` | 不进入 Git；完成报告且实际验证可重建后清理。 |
| 历史报告必需输入 | `reports/<课题键>/<版本>/configs/` | 缺少生成入口时保全，明确复现限制。 |

`analyze_es_robustness.py` 默认生成到 `results/configs/es_robustness/<运行ID>/`。`--generated-config-dir` 接收课题目录，工具追加运行 ID，不覆盖既有配置。报告附件和临时配置的结果均使用临时回测目录。

## 报告附件入口

- [全资产组合优化](../reports/multi_asset_portfolio_optimization/20261101/report.md)
- [中国 ETF 风险平价与境外组合](../reports/china_etf_risk_parity_optimization/20261101/report.md)
- [回撤恢复实验](../reports/drawdown_recovery_experiment/20261101/report.md)
- [全球 QDII 风险平衡](../reports/global_risk_parity_qdii_backtest/20261101/report.md)
- [R038 固定权重阈值](../reports/R038_fixed_weight_threshold/20261101/report.md)
- [R060 ES 稳健性](../reports/R060_es_index_etf_robustness_analysis/20261101/report.md)

附件存在不代表完整复现已验证，具体限制以对应报告为准。不同资金、费用或策略参数的定义独立保存。

当前因子配置执行经验 ES，PCA 使用价格代理因子；不提供 Black-Litterman。算法和输入限制见 [R059 复核报告](../reports/R059_cba21801_index_substitution_sensitivity_analysis/20261102/report.md)。
