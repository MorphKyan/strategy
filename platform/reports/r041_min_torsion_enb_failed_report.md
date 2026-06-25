# R041 基于最小扭转有效押注数约束的风险预算拥挤度控制研究报告

## 结论

结论：`Failed`，不合入。

候选 `risk_parity_min_torsion_enb` 在训练样本主对照中只有轻微收益改善，但日历起点敏感性未通过：`baseline_r2_global_ewma` 与 `baseline_r3_global_nasdaq_all_weather_ewma` 的有效起点平均 Sharpe 均低于基线，且 `ENB/N` 最低值在三组配置中都长期低于冻结阈值 `0.55`。最终测试样本 `2025-07-01` 之后未运行，因为候选在训练样本敏感性阶段已经失败。候选策略源码、注册和平台候选配置已物理清除。

## 假设与来源

假设：在现有 Ledoit-Wolf 风险平价目标权重上，加入 Minimum-Torsion Bets 近似押注空间的 `ENB/N` 约束，可以降低隐含押注拥挤，并在不恶化 Sharpe 与换手的前提下改善最大回撤或起点稳定性。

来源：
- Meucci, `Managing Diversification`：[SSRN 1358533](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1358533)
- Deguest, Martellini, Meucci, `Risk Budgeting and Diversification Based on Optimized Uncorrelated Factors`：[SSRN 2276632](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2276632)

冻结参数：`enb_min_ratio=0.55`、`max_bet_contribution=0.45`、`enb_blend=0.25`、`enb_max_iter=4`、`enb_penalty_strength=0.75`。冻结后未扩展参数搜索。

## 数据与样本隔离

- 当前日期：`2026-06-25`
- 本地行情最新日期：全部所需资产均为 `2026-06-24`，距当前日期 1 天，满足 7 日新鲜度要求。
- 训练样本：截至 `2025-06-30`
- 最终测试样本：自 `2025-07-01` 起，未运行
- 剔除配置：`baseline_r7_cluster_representative_damped` 的共同训练历史仅约 `1.257` 年，不满足超过 3 年要求。

共同训练历史：

| 配置 | 共同起点 | 共同终点 | 至 `2025-06-30` 训练年数 |
| --- | --- | --- | --- |
| `baseline_r2_global_ewma` | `2019-01-18` | `2026-06-24` | `6.448` |
| `baseline_r3_global_nasdaq_all_weather_ewma` | `2020-01-17` | `2026-06-24` | `5.451` |
| `baseline_us_blend_ewma` | `2019-01-18` | `2026-06-24` | `6.448` |
| `baseline_r7_cluster_representative_damped` | `2024-03-28` | `2026-06-24` | `1.257` |

## 训练样本主对照

指标来自实际 `metrics.json`。

| 配置 | 角色 | annualized_return | sharpe_ratio | max_drawdown | annualized_turnover | trade_count | order_count | rejected_order_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `r2_global_ewma` | baseline | `0.144993` | `1.296131` | `-0.114136` | `0.768019` | `335` | `336` | `1` |
| `r2_global_ewma` | candidate | `0.149136` | `1.347178` | `-0.114806` | `0.868034` | `379` | `380` | `1` |
| `r3_global_nasdaq_all_weather_ewma` | baseline | `0.144163` | `0.663707` | `-0.269733` | `0.793515` | `269` | `269` | `0` |
| `r3_global_nasdaq_all_weather_ewma` | candidate | `0.145755` | `0.670602` | `-0.270125` | `0.759905` | `248` | `248` | `0` |
| `us_blend_ewma` | baseline | `0.156574` | `0.836965` | `-0.261594` | `0.689476` | `234` | `234` | `0` |
| `us_blend_ewma` | candidate | `0.163111` | `0.849735` | `-0.265301` | `0.739665` | `253` | `253` | `0` |

主对照显示候选未在单次训练窗口直接失败，但优势很弱：R2 换手率增幅约 `13.0%`，R3 换手下降，US Blend 换手增幅约 `7.3%`；三组最大回撤均略有恶化。

## 日历起点敏感性

采样规则：从各配置最早共同可用交易日起，每 2 个自然月生成一个 `start_date`，所有 run 截止 `2025-06-30`。下表使用 `observations >= 252` 的有效起点统计；完整起点明细保存在 `sensitivity_metrics.csv`。

| 配置 | 角色 | 有效起点数 | Sharpe 均值 | Sharpe Std | max_drawdown 均值 | max_drawdown Std | annualized_turnover 均值 | ENB/N 均值 | ENB/N 最低均值 | 最大单一押注贡献均值 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `r2_global_ewma` | baseline | `32` | `1.856255` | `0.794705` | `-0.086171` | `0.033989` | `0.892959` | `0.798939` | `0.427197` | `0.758868` |
| `r2_global_ewma` | candidate | `32` | `1.851659` | `0.791811` | `-0.087174` | `0.034743` | `0.963214` | `0.805216` | `0.427042` | `0.758153` |
| `r3_global_nasdaq_all_weather_ewma` | baseline | `26` | `1.474648` | `0.847696` | `-0.153903` | `0.111137` | `0.854740` | `0.762058` | `0.316123` | `0.756570` |
| `r3_global_nasdaq_all_weather_ewma` | candidate | `26` | `1.464481` | `0.843742` | `-0.153944` | `0.111181` | `0.799338` | `0.764957` | `0.316062` | `0.753135` |
| `us_blend_ewma` | baseline | `32` | `1.647944` | `1.073309` | `-0.171552` | `0.101683` | `0.736424` | `0.660803` | `0.287621` | `0.840426` |
| `us_blend_ewma` | candidate | `32` | `1.662630` | `1.092863` | `-0.173819` | `0.104830` | `0.768995` | `0.678611` | `0.279489` | `0.859724` |

相对基线：

| 配置 | Sharpe delta 均值 | Sharpe delta Std | Sharpe delta 最小值 | 候选不低于基线起点数 | 换手率相对变化均值 | 换手率相对变化最大值 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `r2_global_ewma` | `-0.004596` | `0.046124` | `-0.151994` | `18/32` | `8.43%` | `18.13%` |
| `r3_global_nasdaq_all_weather_ewma` | `-0.010167` | `0.033098` | `-0.051319` | `5/26` | `-6.35%` | `-1.59%` |
| `us_blend_ewma` | `0.014686` | `0.043800` | `-0.145129` | `26/32` | `4.89%` | `11.63%` |

失败原因：
- R2 与 R3 的有效起点平均 Sharpe 低于基线，不满足训练样本起点稳定性要求。
- `ENB/N` 最低均值远低于冻结阈值 `0.55`，说明约束并未稳定抑制押注拥挤。
- US Blend 虽局部提升 Sharpe，但最大单一押注贡献均值从 `0.840426` 升至 `0.859724`，与拥挤度控制目标相反。
- R2 换手率有效起点最大相对增幅 `18.13%`，超过 15% 门槛。

## Artifact 与配置副本

训练对照 `metrics.json`：
- `D:\strategy\platform\reports\experiments\r041_smoke_r2_train\20260625_094646\metrics.json`
- `D:\strategy\platform\reports\experiments\r041_r3_train\20260625_094715\metrics.json`
- `D:\strategy\platform\reports\experiments\r041_us_blend_train\20260625_094715\metrics.json`

训练对照配置副本：
- `D:\strategy\platform\reports\experiments\r041_smoke_r2_train\20260625_094646\candidate_config.yaml`
- `D:\strategy\platform\reports\experiments\r041_r3_train\20260625_094715\candidate_config.yaml`
- `D:\strategy\platform\reports\experiments\r041_us_blend_train\20260625_094715\candidate_config.yaml`

训练对照 raw artifact：
- candidate R2：`D:\strategy\platform\results\backtests\r041_smoke_r2_train\20260625_094646\risk_parity_min_torsion_enb\r041_min_torsion_enb_r2_global_ewma_candidate_20260625_094646_866936`
- baseline R2：`D:\strategy\platform\results\backtests\r041_smoke_r2_train\20260625_094646\risk_parity_lw_cov\baseline_r2_global_ewma_baseline_20260625_094654_603628`
- candidate R3：`D:\strategy\platform\results\backtests\r041_r3_train\20260625_094715\risk_parity_min_torsion_enb\r041_min_torsion_enb_r3_global_nasdaq_all_weather_ewma_candidate_20260625_094715_670542`
- baseline R3：`D:\strategy\platform\results\backtests\r041_r3_train\20260625_094715\risk_parity_lw_cov\baseline_r3_global_nasdaq_all_weather_ewma_baseline_20260625_094716_845338`
- candidate US Blend：`D:\strategy\platform\results\backtests\r041_us_blend_train\20260625_094715\risk_parity_min_torsion_enb\r041_min_torsion_enb_us_blend_ewma_candidate_20260625_094715_668192`
- baseline US Blend：`D:\strategy\platform\results\backtests\r041_us_blend_train\20260625_094715\risk_parity_lw_cov\baseline_us_blend_ewma_baseline_20260625_094716_843648`

敏感性：
- 汇总目录：`D:\strategy\platform\reports\r041_calendar_sensitivity\20260625_094903`
- 汇总 CSV：`D:\strategy\platform\reports\r041_calendar_sensitivity\20260625_094903\sensitivity_metrics.csv`
- 汇总 JSON：`D:\strategy\platform\reports\r041_calendar_sensitivity\20260625_094903\summary.json`
- 原始 artifact 根目录：`D:\strategy\platform\results\sensitivity_raw\r041_calendar\20260625_094903`

## 执行命令

```powershell
.\env\python.exe -m py_compile platform\src\platform_core\strategy.py
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\r041_min_torsion_enb_r2_global_ewma.yaml --baseline-config configs\baseline_r2_global_ewma.yaml --experiment-name r041_smoke_r2_train --start-date 2019-01-18 --end-date 2025-06-30 --no-charts
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\r041_min_torsion_enb_r3_global_nasdaq_all_weather_ewma.yaml --baseline-config configs\baseline_r3_global_nasdaq_all_weather_ewma.yaml --experiment-name r041_r3_train --start-date 2020-01-17 --end-date 2025-06-30 --no-charts
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\r041_min_torsion_enb_us_blend_ewma.yaml --baseline-config configs\baseline_us_blend_ewma.yaml --experiment-name r041_us_blend_train --start-date 2019-01-18 --end-date 2025-06-30 --no-charts
.\env\python.exe tmp_r041_calendar_sensitivity.py
```

数据新鲜度与共同区间检查使用 `.\env\python.exe -` 内联脚本读取配置和 `platform/data/*.csv` 完成；未发生数据同步。

## 文件处理

已清理：
- `platform/src/platform_core/strategy.py` 中的 `RiskParityMinimumTorsionENBStrategy` 与 `BUILTIN_STRATEGIES` 注册。
- `platform/configs/r041_min_torsion_enb_r2_global_ewma.yaml`
- `platform/configs/r041_min_torsion_enb_r3_global_nasdaq_all_weather_ewma.yaml`
- `platform/configs/r041_min_torsion_enb_us_blend_ewma.yaml`
- 临时脚本 `tmp_r041_calendar_sensitivity.py` 已删除。

保留：
- 已生成 raw artifacts、标准实验报告、敏感性汇总和 `r041_enb_diagnostics.csv`，供 reviewer 复核。
