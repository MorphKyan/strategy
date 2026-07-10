# R043：Gerber 风险平价的长久期趋势保护策略研究报告

> 结论：`Failed`。候选没有通过训练主窗口的显著改善门槛，并在完整起点敏感性中稳定退化；按预冻结规则未运行最终测试，候选源码、注册和配置已清理。

完整文件归属、测试时间戳、清理核验、模型元数据与 diff-check 证据见 [R043 证据附录](r043_evidence_appendix.md)。

## 一、冻结假设与实现

候选完全继承 `baseline_risk_parity_gerber.yaml` 的三资产篮子、`rolling_window=120`、`min_periods=20`、`gerber_c=0.5`、月度再平衡和 `0.05/0.25` 阈值。月末目标生成时，只使用前一交易日及以前的未杠杆 `511260.SH` 后复权价格：252 日总收益严格为正时保留 `511260_3X.SH` 的 Gerber 原始权重，否则乘以 `1/3`，释放资金留现金。没有搜索窗口、档位、资产、阈值或新增确认规则。

候选通过 `Strategy.generate_targets(context)` 路径增量实现。每期审计记录 `signal_cutoff`、252 日收益、multiplier、原始/最终债券权重和理论现金权重。训练失败后实现、注册和候选配置均已删除，历史 raw 中的 `config_snapshot.yaml` 可复核原样规则。

## 二、数据与隔离证据

- `510300`、`518880`、`511260`、`511260_3X` 均最新至 `2026-07-10`，重复日期均为 0；无需同步。
- 四者共同训练区间为 `2017-08-24` 至 `2025-06-30`，1902 个共同交易日，约 7.85 年，超过三年门槛。
- 当前平台 CSV 和共同日历检查实际通过。`validate_hfq_data.py` 失败是因为已废弃的旧对照源 `research/data/510300.csv` 不存在，不能解释为当前平台数据不对齐；本研究明确记录这一外部 HFQ 对照缺口。
- 数据 SHA256（前缀）：`510300=1290ACD2...`、`518880=3269284E...`、`511260=D4F9BDD7...`、`511260_3X=6B4F0A3D...`；研究代码基线 commit 为 `0dbed68949f2ddcedbe7d4616c7700722394b5f7`。
- 训练只截止 `2025-06-30`。训练失败后未运行或读取最终测试指标。

## 三、主训练三滑点结果

| 滑点 | 组合 | annualized_return | annualized_volatility | sharpe_ratio | max_drawdown | annualized_turnover | trade/order/rejected | max_pending | average_cash_weight |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | 基线 | 12.09% | 6.73% | 1.796 | -7.78% | 32.60% | 83/83/0 | 3 | 2.00% |
| default | 候选 | 11.84% | 6.61% | 1.791 | -8.48% | 36.25% | 85/85/0 | 3 | 6.12% |
| stress | 基线 | 11.91% | 6.72% | 1.772 | -7.80% | 32.57% | 87/87/0 | 3 | 2.10% |
| stress | 候选 | 11.71% | 6.60% | 1.774 | -8.50% | 36.29% | 84/84/0 | 3 | 6.19% |
| dynamic_participation | 基线 | 12.02% | 6.73% | 1.787 | -7.79% | 32.60% | 86/86/0 | 3 | 2.06% |
| dynamic_participation | 候选 | 11.83% | 6.61% | 1.790 | -8.48% | 36.36% | 87/87/0 | 3 | 6.12% |

Sharpe 差依次为 `-0.0049/+0.0023/+0.0029`，均未低于 `-0.05`，但没有两个场景提升至少 `0.05`；三个场景回撤反而恶化约 0.69 个百分点，也不满足回撤收窄 10% 的替代条件。换手增幅约 11%~12%，未超过 30%；拒单为 0，执行本身没有触发失败。

实际指标路径：

- `platform/reports/experiments/r043_training_default/20260711_001945/metrics.json`
- `platform/reports/experiments/r043_training_stress/20260711_001948/metrics.json`
- `platform/reports/experiments/r043_training_dynamic_participation/20260711_001951/metrics.json`

## 四、严格自然月起点敏感性

从 `2017-08-24` 起每两个月生成锚点并取其后首个共同交易日，共 48 个起点。正式统计的基线和候选各运行 48×3=144 runs，总计 288 runs，失败 0。首次工具调用在调用层超时，但其子进程继续完成了额外的完整 144-run 基线批次 `20260711_002014`；随后重启的独立完整基线批次 `20260711_002033` 作为正式统计口径。重复批次按程序时间戳选定而非按表现择优，并按不覆盖历史产物原则保留。

| 滑点 | Sharpe差中位数 | 差值≥-0.05比例 | 候选/基线 Sharpe std | 候选/基线 MDD std | 年化收益差中位数 | 换手增幅中位数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| default | -0.108 | 20.8% | 0.567/0.754 | 2.21%/2.33% | -1.00个百分点 | -0.57% |
| stress | -0.109 | 22.9% | 0.578/0.770 | 2.21%/2.33% | -1.01个百分点 | +0.09% |
| dynamic_participation | -0.108 | 22.9% | 0.568/0.755 | 2.21%/2.33% | -0.99个百分点 | -0.57% |

三个场景的 Sharpe 差中位数均低于 0，且远少于 80% 的起点达到 `-0.05` 下限，敏感性硬失败。标准产物：

- `platform/reports/sensitivity/r043/risk_parity_gerber/20260711_002033/`
- `platform/reports/sensitivity/r043/risk_parity_gerber_duration_trend/20260711_002223/`
- raw：`platform/results/sensitivity_raw/r043/`

## 五、信号、现金和金融解释

每个训练场景记录 94 次月度信号，其中低档 16 次、高档 78 次，仅切换 3 次；所有 `signal_cutoff` 严格早于目标生成日，前视违规为 0。理论释放现金权重均值约 4.31%、最大约 39.08%；实际 `average_cash_weight` 从基线约 2% 上升至约 6.1%。

该规则降低了部分久期波动，却在多数起点损失了债券趋势收益，现金拖累超过波动下降带来的收益风险比改善。二元 252 日信号对中国利率周期转折较慢，而且 10Y ETF 趋势不能完整代表 30Y 曲线、久期与凸性；虚拟资产也没有建模 TL 期货基差、CTD、展期、融资、保证金和真实流动性。结果表明，该简单保护层不能稳健改进 Gerber 风险平价。

## 六、精确命令、测试与处理

```powershell
.\env\python.exe platform\scripts\validate_hfq_data.py --codes 510300 518880 511260
.\env\python.exe -m pytest platform\tests -q
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\baseline_risk_parity_gerber.yaml --start-date 2017-08-24 --end-date 2025-06-30 --slippage-scenario all
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\candidate_r043_gerber_duration_trend.yaml --start-date 2017-08-24 --end-date 2025-06-30 --slippage-scenario all
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\candidate_r043_gerber_duration_trend.yaml --baseline-config configs\baseline_risk_parity_gerber.yaml --experiment-name r043_training --start-date 2017-08-24 --end-date 2025-06-30 --slippage-scenario all --no-charts
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\baseline_risk_parity_gerber.yaml --end-date 2025-06-30 --calendar-month-step 2 --slippage-scenario all --raw-root results\sensitivity_raw\r043 --report-root reports\sensitivity\r043
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\candidate_r043_gerber_duration_trend.yaml --end-date 2025-06-30 --calendar-month-step 2 --slippage-scenario all --raw-root results\sensitivity_raw\r043 --report-root reports\sensitivity\r043
```

测试结果为 `63 passed`。因训练失败，没有冻结候选供最终测试，也没有运行 `2025-07-01` 之后的最终测试。最终保留中文报告、研究笔记、标准指标和 raw artifacts；删除 `platform/configs/candidate_r043_gerber_duration_trend.yaml`，并从 `platform/src/platform_core/strategy.py` 清除候选类与注册，未留下临时脚本。
