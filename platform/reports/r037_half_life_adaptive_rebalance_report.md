# R037 基于波动率半衰期衰减动态阈值触发的自适应再平衡风险平价策略报告

## 结论

本课题判定为 `Failed`，不合入主干，不保留策略注册或平台配置。

候选逻辑在 R016 `adaptive_risk_deviation_volatility_triggered` 的基础上，将动态再平衡阈值替换为基于资产 realized volatility AR(1) 自相关估计的半衰期公式，并冻结参数为 `half_life_window=120`、`half_life_vol_window=20`、`half_life_gamma=5.0`、`rebalance_fraction=0.8`。训练样本对照显示，候选在两个验证配置上均发生 Sharpe 退化和最大回撤恶化，虽年化换手率略降，但交易笔数上升，未达到 R037 的验收条件。

最终测试样本未运行。原因是候选在 `2025-06-30` 及以前训练样本已未通过门槛；按样本隔离规则，不使用 `2025-07-01` 之后结果为失败候选背书或反向修改参数。

## 数据新鲜度与样本隔离

- 当前日期：`2026-06-24`
- 新鲜度门槛：最新本地日期不早于 `2026-06-17`
- 覆盖 symbol：`510300`、`512890`、`513500`、`518880`、`511260_3X`
- 本地最新日期：全部为 `2026-06-24`
- 共同交易区间：`2019-01-18` 至 `2026-06-24`
- 训练样本上限：`2025-06-30`
- 最终测试起点：`2025-07-01`
- 共同训练历史：超过 3 年

## 假设与来源

- 假设：波动率半衰期短时，市场冲击衰减快，阈值应收窄以更快接近新风险平价权重；半衰期长时，市场处于高波震荡或慢衰减状态，阈值可相对放宽以减少 whipsaw。
- 来源：R016 已验证动态偏离阈值和系统波动触发能降低换手并改善风险表现；R026/R028 显示刚性惩罚或迟滞过强会导致权重锁死和避险滞后。本课题仅在 R016 相邻范围内验证半衰期阈值替代，不引入大规模参数搜索。

## 训练样本对照指标

指标读取自：

- `platform/reports/experiments/r037_r1_halflife_vs_r016_train/20260624_235300/metrics.json`
- `platform/reports/experiments/r037_r2_halflife_vs_r016_train/20260624_235300/metrics.json`

| 配置 | 策略 | annualized_return | sharpe_ratio | max_drawdown | annualized_turnover | trade_count | order_count | rejected_order_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| r1 domestic rolling | R016 基线 | 0.1388 | 1.2926 | -0.1422 | 0.3467 | 115 | 116 | 1 |
| r1 domestic rolling | R037 候选 | 0.1408 | 1.2557 | -0.1528 | 0.3229 | 179 | 179 | 0 |
| r2 global dividend ewma | R016 基线 | 0.1531 | 1.0953 | -0.1591 | 0.3358 | 159 | 161 | 2 |
| r2 global dividend ewma | R037 候选 | 0.1498 | 1.0196 | -0.1834 | 0.3143 | 210 | 211 | 1 |

训练样本结论：

- `r1` Sharpe 下降 `-0.0370`，最大回撤恶化 `-1.06%`；年化换手下降 `-0.0237`，但交易笔数增加 `+64`。
- `r2` Sharpe 下降 `-0.0757`，最大回撤恶化 `-2.43%`；年化换手下降 `-0.0215`，但交易笔数增加 `+51`。
- 候选没有满足“相比 R016 Sharpe 不退化、最终换手低于 R016 的 85%、最大回撤无显著恶化”的训练样本前置条件。

## 起点敏感性

指标读取自：

- `platform/reports/sensitivity/r037_half_life/20260624_235524/sensitivity_summary.csv`
- `platform/reports/sensitivity/r037_half_life/20260624_235524/sensitivity_stats.json`

采样规则：从共同可用交易日开始，每 2 个自然月取下一个可用交易日，所有 run 截止 `2025-06-30`。尾端 `2025-05-19` 起点剩余样本过短，Sharpe 为 `0.0`，报告中保留但不作为优势证据。

| 配置 | 策略 | 样本数 | Sharpe 均值 | Sharpe Std | MaxDD 均值 | MaxDD Std | 年化换手均值 | trade_count 均值 | order_count 均值 | rejected_order_count 均值 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| r1 | R016 基线 | 39 | 2.0962 | 0.9479 | -0.0768 | 0.0565 | 0.5808 | 70.26 | 70.67 | 0.41 |
| r1 | R037 候选 | 39 | 2.0897 | 0.9583 | -0.0792 | 0.0605 | 0.5459 | 98.36 | 98.44 | 0.08 |
| r2 | R016 基线 | 39 | 1.8948 | 0.9705 | -0.0982 | 0.0589 | 0.5433 | 75.28 | 76.13 | 0.85 |
| r2 | R037 候选 | 39 | 1.9096 | 1.0116 | -0.1033 | 0.0645 | 0.5066 | 96.28 | 96.38 | 0.10 |

敏感性结论：

- `r1` 候选相对 R016 的 Sharpe 差值均值为 `-0.0065`，39 个起点中仅 14 个优于基线；最大回撤均值和波动均恶化。
- `r2` 候选 Sharpe 差值均值为 `+0.0148`，但最差起点为 `-0.1783`，且 Sharpe Std 从 `0.9705` 升至 `1.0116`，MaxDD 均值和波动均恶化。
- 候选并未降低路径敏感性；换手率略低的同时，交易笔数和订单数显著上升，执行摩擦结构变差。

## 原始 artifacts 与标准报告

- R1 标准报告：`platform/reports/experiments/r037_r1_halflife_vs_r016_train/20260624_235300/`
- R1 候选 raw：`platform/results/backtests/r037_r1_halflife_vs_r016_train/20260624_235300/half_life_adaptive_risk_parity/research_r037_r1_halflife_train_candidate_20260624_235300_491705/`
- R1 基线 raw：`platform/results/backtests/r037_r1_halflife_vs_r016_train/20260624_235300/adaptive_risk_deviation_volatility_triggered/research_r037_r1_r016_train_baseline_20260624_235315_993879/`
- R2 标准报告：`platform/reports/experiments/r037_r2_halflife_vs_r016_train/20260624_235300/`
- R2 候选 raw：`platform/results/backtests/r037_r2_halflife_vs_r016_train/20260624_235300/half_life_adaptive_risk_parity/research_r037_r2_halflife_train_candidate_20260624_235300_491546/`
- R2 基线 raw：`platform/results/backtests/r037_r2_halflife_vs_r016_train/20260624_235300/adaptive_risk_deviation_volatility_triggered/research_r037_r2_r016_train_baseline_20260624_235317_021250/`
- 敏感性报告：`platform/reports/sensitivity/r037_half_life/20260624_235524/`
- 敏感性 raw：`platform/results/sensitivity_raw/r037_half_life/20260624_235524/`

## 执行命令

```powershell
.\env\python.exe platform\scripts\get_common_date_range.py --config platform\configs\baseline_r1_domestic_rolling.yaml platform\configs\global_dividend_ewma.yaml
.\env\python.exe -m compileall platform\src\platform_core\strategy.py
.\env\python.exe platform\scripts\get_common_date_range.py --config platform\configs\research_r037_r1_halflife_train.yaml platform\configs\research_r037_r2_halflife_train.yaml
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\research_r037_r1_halflife_train.yaml --baseline-config configs\research_r037_r1_r016_train.yaml --experiment-name r037_r1_halflife_vs_r016_train --no-charts
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\research_r037_r2_halflife_train.yaml --baseline-config configs\research_r037_r2_r016_train.yaml --experiment-name r037_r2_halflife_vs_r016_train --no-charts
```

起点敏感性通过内联 Python 调用 `src.platform_core.experiment.run_backtest` 完成，未新增持久化脚本。原始完整 inline Python 命令文本未在归档产物中保留，无法逐字符恢复。可审计复现形态如下：在 `D:\strategy` 下使用 `.\env\python.exe -` 执行内联 Python，读取 `research_r037_r1_r016_train`、`research_r037_r1_halflife_train`、`research_r037_r2_r016_train`、`research_r037_r2_halflife_train` 四组训练配置或 raw 目录中的 `config_snapshot.yaml`，将每个 run 的 `start_date` 设为从共同可用交易日起每 2 个自然月的下一个可用交易日，将 `end_date` 固定为 `2025-06-30`，并分别以 `r1/baseline_r016`、`r1/candidate_halflife`、`r2/baseline_r016`、`r2/candidate_halflife` 调用 `src.platform_core.experiment.run_backtest(runtime_config, "sensitivity", store, raw_dir / start_date, render_charts=False)`；汇总输出为 `sensitivity_summary.csv` 和 `sensitivity_stats.json`。

敏感性标准报告目录：`D:\strategy\platform\reports\sensitivity\r037_half_life\20260624_235524`。

敏感性 raw artifacts 目录：`D:\strategy\platform\results\sensitivity_raw\r037_half_life\20260624_235524`。

## 代码与清理

- 临时实现过 `half_life_adaptive_risk_parity` 并注册用于训练样本实验。
- 因训练样本和敏感性未通过，已从 `platform/src/platform_core/strategy.py` 物理移除候选策略与注册。
- 临时研究配置 `platform/configs/research_r037_*_train.yaml` 已删除。
- 未保留新的平台 baseline 配置。

## 推荐

拒绝合入。半衰期阈值把 R016 原本稳定的波动率比值门控改成了更复杂的路径估计，但未带来稳定的 Sharpe 或回撤改善；部分起点和配置虽有局部收益，整体被更高交易笔数、回撤恶化和路径敏感性上升抵消。后续若继续研究动态阈值，应优先约束交易笔数和避险滞后，而不是只追求年化换手率下降。
