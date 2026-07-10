# R043 文件与验证证据附录

本附录仅补充文档和自动化测试证据，不改变候选逻辑、指标、产物、验收门槛或 `Failed` 结论，也没有运行任何回测或最终测试。

## 一、R043 文件归属清单

### R043 创建并保留

- `platform/reports/r043_gerber_duration_trend_report.md`：中文主报告。
- `platform/reports/r043_evidence_appendix.md`：本证据附录。
- `research-dashboard/notes/R043_Gerber风险平价长久期趋势保护.md`：中文研究笔记。
- `platform/reports/experiments/r043_training_default/20260711_001945/`：`default` 标准化训练指标与报告。
- `platform/reports/experiments/r043_training_stress/20260711_001948/`：`stress` 标准化训练指标与报告。
- `platform/reports/experiments/r043_training_dynamic_participation/20260711_001951/`：`dynamic_participation` 标准化训练指标与报告。
- `platform/reports/sensitivity/r043/risk_parity_gerber/20260711_002014/`：调用层超时后仍完成的额外完整基线诊断批次，未纳入正式统计。
- `platform/reports/sensitivity/r043/risk_parity_gerber/20260711_002033/`：正式基线敏感性批次。
- `platform/reports/sensitivity/r043/risk_parity_gerber_duration_trend/20260711_002223/`：正式候选敏感性批次。
- `platform/results/backtests/r043_training_default/20260711_001945/`、`r043_training_stress/20260711_001948/`、`r043_training_dynamic_participation/20260711_001951/`：标准化训练 raw artifacts。
- `platform/results/sensitivity_raw/r043/`：敏感性 raw artifacts，包括额外完整基线诊断与正式批次。
- `platform/results/backtests/platform_risk_parity_gerber_*_20260711_0019*/` 与 `platform/results/backtests/candidate_r043_gerber_duration_trend_*_20260711_0019*/`：主训练前的直接 backtest raw 证据；未覆盖或删除。

### R043 修改并保留

- `research-dashboard/research_backlog.md`：R043 从 Todo 到 In-Progress，再归档为 Completed/Failed。
- `research-dashboard/research_history_summary.md`：追加 R043 失败摘要。
- `platform/reports/non_baseline_research_history_summary.md`：追加 R043 失败摘要。
- `platform/reports/r043_gerber_duration_trend_report.md` 与研究笔记：本轮仅追加本附录链接。

### R043 创建后删除或清理

- `platform/configs/candidate_r043_gerber_duration_trend.yaml`：训练使用的候选配置；失败后删除。原样快照保留在 raw artifacts。
- `RiskParityGerberDurationTrendStrategy`、注册键 `risk_parity_gerber_duration_trend`：研究期间临时加入 `platform/src/platform_core/strategy.py`，失败后完整清除。
- `platform/src/platform_core/engine.py` 中临时 `strategy_signals.csv` 输出行：失败后清除；信号审计 CSV 仅保留在既有 raw artifacts。
- R043 没有创建任务专用脚本，因此无临时脚本文件需要删除。

### 明确不属于 R043 的预先存在或并行修改

- `platform/data/511260_3X.csv`：R042 已生成/更新的虚拟资产数据；R043 只读使用，没有同步或重建。
- `platform/scripts/run_sensitivity.py`：R042 已保留的可复用自然月敏感性功能修改；R043 仅调用，没有修改。
- `platform/src/platform_dashboard/app.py`、`platform/src/platform_dashboard/artifacts.py`：既有并行 dashboard 修改；R043 没有编辑。
- `platform/reports/r042_evidence_and_command_appendix.md`、`r042_freeze_20260710_211100.md`、`r042_virtual_30y_permanent_portfolio_report.md`、`platform/reports/sensitivity/r042/`、`research-dashboard/notes/R042_虚拟30年国债中国永久组合.md`：R042 历史产物，R043 没有编辑。
- 当前 `git status` 将 `platform/src/platform_core/engine.py`、`strategy.py` 标为修改，但 `git diff --` 对两文件没有文本差异；R043 候选内容已清零，不能把工作树的行尾/索引状态归为保留的 R043 代码变更。

## 二、自动化测试证据

- 命令：`.\env\python.exe -m pytest platform\tests -q`
- 开始：`2026-07-11T00:30:55+08:00`
- 结束：`2026-07-11T00:31:01+08:00`
- exit code：`0`
- 完整有效输出：

```text
...............................................................          [100%]
63 passed in 4.86s
```

测试结果仍为 63 项通过。本轮没有运行 backtest、experiment、sensitivity 或 OOS 命令。

## 三、候选清理复核

执行命令：

```powershell
Test-Path platform\configs\candidate_r043_gerber_duration_trend.yaml
rg -n "RiskParityGerberDurationTrendStrategy|risk_parity_gerber_duration_trend" platform\src platform\configs
Get-ChildItem platform\scripts -File | Where-Object {$_.Name -match 'r043|duration.*trend|trend.*duration'} | Select-Object FullName
```

实际结果：

```text
False
RG_EXIT=1
TEMP_SCRIPTS
```

即候选 YAML 不存在；源码和配置中没有候选类或注册键匹配；没有 R043/久期趋势任务专用脚本。

## 四、diff-check 与脏文件归因

R043 涉及的 tracked 文档范围检查：

```powershell
git diff --check -- platform/reports/non_baseline_research_history_summary.md research-dashboard/research_backlog.md research-dashboard/research_history_summary.md
```

结果：`SCOPED_EXIT=0`，无错误。

全局检查：

```powershell
git diff --check
```

结果：`GLOBAL_EXIT=2`，仅报告：

```text
platform/src/platform_dashboard/app.py:553: trailing whitespace.
platform/src/platform_dashboard/app.py:556: trailing whitespace.
platform/src/platform_dashboard/artifacts.py:111: trailing whitespace.
```

这些 dashboard 尾随空格来自 R043 开始前已经存在的并行脏修改；R043 未编辑这两个文件，因此没有代为修复或归因给 R043。全局命令还显示换行格式 warning，但不属于 `diff --check` 内容错误。

## 五、模型与思考强度元数据

用户要求 researcher 使用 `gpt-5.6-terra` 且 reasoning effort 为 `medium`。当前子代理运行时没有暴露可验证的模型名称或思考强度元数据，因此无法验证实际运行是否为 `gpt-5.6-terra medium`；本报告不作已验证声明。

## 六、最终状态

- 结论保持 `Failed`。
- 没有修改指标、阈值、候选逻辑或历史 artifacts。
- 没有运行或读取最终测试。
- 没有候选 YAML、候选类、注册键或临时脚本残留。
