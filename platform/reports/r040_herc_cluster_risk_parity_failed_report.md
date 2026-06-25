# R040 HERC 簇级风险预算风险平价研究报告

## 结论

`R040` 判定为 `Failed`。候选 `herc_cluster_risk_parity` 未通过训练样本主对照和日历起点敏感性，不进入最终测试样本验证，不保留策略注册、候选源码或平台候选配置。

## 假设与冻结设定

研究假设是：按 sleeve 先做簇级等风险贡献，再在簇内做风险平价，可以减少同类资产数量不均导致的风险预算拥挤。候选设定在训练评估前冻结：`cluster_weight_cap=0.55`、`shrinkage_target=constant_correlation`，配置内使用固定 `sleeve_mapping`，不做大规模参数搜索。

训练样本固定截至 `2025-06-30`。最终测试样本为 `2025-07-01` 之后；由于候选未通过训练和敏感性门槛，最终测试未运行。

## 数据核验

当前日期 `2026-06-25`。R040 相关 symbol 本地最新日期均为 `2026-06-24`：`510300`、`512890`、`513500`、`513100`、`518880`、`511260_3X`、`159985`、`159981`、`510310`。距当前日期 1 天，满足 7 日新鲜度规则。

共同训练历史均超过三年：
- `r2`：训练共同区间 `2019-01-18` 至 `2025-06-30`，`1559` 个共同交易日。
- `r3`：训练共同区间 `2020-01-17` 至 `2025-06-30`，`1316` 个共同交易日。
- `r7`：训练共同区间 `2020-01-17` 至 `2025-06-30`，`1317` 个共同交易日。

## 训练样本主对照

指标来自实际 `metrics.json`：

| 配置 | metrics.json | Baseline Sharpe | Candidate Sharpe | Baseline MaxDD | Candidate MaxDD | Baseline annualized_turnover | Candidate annualized_turnover | trade_count | order_count | rejected_order_count |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `r2` | `platform/reports/experiments/r040_herc_cluster_r2_train/20260625_091924/metrics.json` | `1.1876` | `1.2006` | `-10.66%` | `-13.00%` | `0.8160` | `0.7521` | `282` | `283` | `1` |
| `r3` | `platform/reports/experiments/r040_herc_cluster_r3_train/20260625_091924/metrics.json` | `0.6637` | `0.5833` | `-26.97%` | `-31.11%` | `0.7935` | `0.6627` | `216` | `216` | `0` |
| `r7` | `platform/reports/experiments/r040_herc_cluster_r7_train/20260625_091924/metrics.json` | `1.2984` | `1.3096` | `-14.17%` | `-14.98%` | `0.3974` | `0.3737` | `93` | `93` | `0` |

训练结论：`r3` Sharpe 明确退化，且 `r2/r3/r7` 最大回撤全部恶化。候选没有满足“主要多资产配置 Sharpe 不得退化；若持平则最大回撤或敏感性需显著改善”的门槛。

## 起点敏感性

指标来自 `platform/reports/r040_calendar_sensitivity/20260625_093633/sensitivity_stats.csv`：

| 标签 | runs | Sharpe mean | Sharpe std | annualized_return mean | MaxDD mean | MaxDD std | annualized_turnover mean | trade_count mean | order_count mean | rejected_order_count mean |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `r2_baseline` | `39` | `1.8887` | `0.8488` | `15.57%` | `-7.66%` | `3.79%` | `0.9679` | `187.54` | `188.23` | `0.69` |
| `r2_candidate` | `39` | `1.9540` | `0.8531` | `15.64%` | `-8.49%` | `4.53%` | `0.9243` | `178.18` | `178.87` | `0.69` |
| `r3_baseline` | `33` | `1.5059` | `0.8643` | `13.73%` | `-12.84%` | `11.05%` | `0.9277` | `133.06` | `133.06` | `0.00` |
| `r3_candidate` | `33` | `1.6853` | `1.0442` | `14.91%` | `-13.94%` | `13.49%` | `0.8020` | `109.67` | `109.67` | `0.00` |
| `r7_baseline_3x` | `33` | `1.6883` | `0.4901` | `25.58%` | `-7.66%` | `5.44%` | `0.6103` | `50.09` | `50.09` | `0.00` |
| `r7_candidate_3x` | `33` | `1.6350` | `0.5015` | `23.61%` | `-8.23%` | `5.43%` | `0.5978` | `55.09` | `55.09` | `0.00` |

敏感性结论：候选 Sharpe 标准差分别为 `0.8531`、`1.0442`、`0.5015`，均显著高于 R040 门槛 `0.25`；最大回撤标准差也均高于 `2%`。`r7_candidate_3x` 的敏感性 Sharpe 均值低于基线，且交易笔数上升。敏感性失败。

## Artifacts

标准实验报告：
- `platform/reports/experiments/r040_herc_cluster_r2_train/20260625_091924/`
- `platform/reports/experiments/r040_herc_cluster_r3_train/20260625_091924/`
- `platform/reports/experiments/r040_herc_cluster_r7_train/20260625_091924/`
- `platform/reports/r040_calendar_sensitivity/20260625_093633/`

原始结果目录：
- `D:\strategy\platform\results\backtests\r040_herc_cluster_r2_train\20260625_091924\herc_cluster_risk_parity\r040_herc_cluster_r2_global_ewma_candidate_20260625_091924_878491`
- `D:\strategy\platform\results\backtests\r040_herc_cluster_r2_train\20260625_091924\risk_parity_lw_cov\baseline_r2_global_ewma_baseline_20260625_091931_742995`
- `D:\strategy\platform\results\backtests\r040_herc_cluster_r3_train\20260625_091924\herc_cluster_risk_parity\r040_herc_cluster_r3_global_nasdaq_all_weather_ewma_candidate_20260625_091924_992164`
- `D:\strategy\platform\results\backtests\r040_herc_cluster_r3_train\20260625_091924\risk_parity_lw_cov\baseline_r3_global_nasdaq_all_weather_ewma_baseline_20260625_091926_234763`
- `D:\strategy\platform\results\backtests\r040_herc_cluster_r7_train\20260625_091924\herc_cluster_risk_parity\r040_herc_cluster_r7_cluster_representative_damped_3x_candidate_20260625_091924_958871`
- `D:\strategy\platform\results\backtests\r040_herc_cluster_r7_train\20260625_091924\cluster_representative_damped_risk_parity\r040_baseline_r7_cluster_representative_damped_3x_baseline_20260625_091926_060215`
- `D:\strategy\platform\results\r040_calendar_sensitivity_raw\20260625_093633`

## 命令记录

本次续作核验命令：

```powershell
@'
# 读取 R040 metrics.json、sensitivity_stats.csv 并核验数据日期
'@ | .\env\python.exe -
.\env\python.exe -m py_compile platform\src\platform_core\strategy.py
```

既有 R040 标准实验由以下入口生成，样本上限均为 `2025-06-30`：

```powershell
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\r040_herc_cluster_r2_global_ewma.yaml --baseline-config configs\baseline_r2_global_ewma.yaml --experiment-name r040_herc_cluster_r2_train --start-date 2020-01-17 --end-date 2025-06-30
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\r040_herc_cluster_r3_global_nasdaq_all_weather_ewma.yaml --baseline-config configs\baseline_r3_global_nasdaq_all_weather_ewma.yaml --experiment-name r040_herc_cluster_r3_train --start-date 2020-01-17 --end-date 2025-06-30
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\r040_herc_cluster_r7_cluster_representative_damped_3x.yaml --baseline-config configs\r040_baseline_r7_cluster_representative_damped_3x.yaml --experiment-name r040_herc_cluster_r7_train --start-date 2020-01-17 --end-date 2025-06-30
.\env\python.exe tmp_r040_calendar_sensitivity.py
```

`tmp_r040_calendar_sensitivity.py` 已在完成后删除，未作为可维护平台工具保留。

## 文件处理

已物理清除：
- `platform/src/platform_core/strategy.py` 中的 `HERCClusterRiskParityStrategy`
- `BUILTIN_STRATEGIES` 中的 `herc_cluster_risk_parity` 注册
- `platform/configs/r040_baseline_r7_cluster_representative_damped_3x.yaml`
- `platform/configs/r040_herc_cluster_r2_global_ewma.yaml`
- `platform/configs/r040_herc_cluster_r3_global_nasdaq_all_weather_ewma.yaml`
- `platform/configs/r040_herc_cluster_r7_cluster_representative_damped_3x.yaml`
- `tmp_r040_calendar_sensitivity.py`

保留：
- 既有 R040 标准实验报告
- 既有 R040 原始回测 artifacts
- 既有 R040 日历敏感性 artifacts

## 建议

不合入 R040。HERC 簇级预算在该实现下能降低部分换手，但没有换来稳定的风险调整收益；在 `r3` 主训练窗口中明显退化，并在起点敏感性中表现出强路径依赖。后续若继续研究层级预算，应优先改为可解释的动态簇风险贡献审计工具，而不是直接保留为可交易策略。
