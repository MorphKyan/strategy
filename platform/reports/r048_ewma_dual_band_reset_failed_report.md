# R048：EWMA 风险平价外带触发、内带复位的双边界脉冲再平衡

## 结论

`Failed`。候选在主训练样本的三个强制滑点场景都降低了成交金额换手，但都增加了 `trade_count` 和 `order_count`，直接违反预冻结硬门槛。未运行低波、等权稳健性配置、自然月起点敏感性或最终测试；未读取 `2025-07-01` 之后的策略表现。候选源码、注册、测试和配置均已物理清理。

## 假设与预注册规则

候选 `risk_parity_ewma_dual_band_reset` 保留 `risk_parity_ewma` 的月频检查、EWMA 参数和 5%/25% 外带；越界时以 `b_inner=0.5*b_outer` 和最小线性 `alpha` 回到内带。固定比例 `0.5` 是首次回测前冻结的工程近似，并非理论最优。理论依据为固定成本与比例成本同时存在时成交可落在无交易区内部（Holden & Holden, 2011；Dybvig & Pezzo, 2019）。

## 数据、范围与命令

- 数据快照：四个相关本地 CSV 的 `updated_at` 为 2026-07-10；运行日为 2026-07-11，满足 7 日新鲜度。无重复 `trade_date`、非正 OHLC 或非正 `adjust_factor`。
- 训练区间：`2019-01-18` 至 `2025-06-30`，1561 个观察；共同历史严格超过三年。
- 主基线：`platform/configs/baseline_r1_domestic_ewma.yaml`。
- 候选临时配置：`platform/configs/r048_domestic_ewma_dual_band_reset.yaml`（已清理）。

```powershell
.\env\python.exe -m pytest platform\tests\test_platform_strategies.py platform\tests\test_r048_dual_band_reset.py -q
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\r048_domestic_ewma_dual_band_reset.yaml --baseline-config configs\baseline_r1_domestic_ewma.yaml --experiment-name r048_training_domestic --start-date 2019-01-18 --end-date 2025-06-30 --slippage-scenario all --no-charts
```

候选单元测试在清理前为 `13 passed`，覆盖注册、初始完整建仓、外带触发后的最小 `alpha` 内带投影与零目标退出。

## 主训练实际产物指标

| 场景 | 策略 | annualized_return | sharpe_ratio | max_drawdown | annualized_turnover | trade_count | order_count | rejected_order_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | 基线 | 14.882% | 2.0309 | -7.702% | 60.931% | 164 | 164 | 0 |
| default | 候选 | 14.733% | 2.0348 | -7.683% | 49.223% | 171 | 171 | 0 |
| stress | 基线 | 14.728% | 2.0146 | -7.700% | 60.789% | 164 | 164 | 0 |
| stress | 候选 | 14.566% | 2.0194 | -7.680% | 49.868% | 175 | 175 | 0 |
| dynamic_participation | 基线 | 14.861% | 2.0329 | -7.702% | 60.263% | 162 | 162 | 0 |
| dynamic_participation | 候选 | 14.708% | 2.0310 | -7.684% | 49.191% | 170 | 170 | 0 |

候选的年化换手降低约 10.9 至 11.7 个百分点，Sharpe 差为 `+0.0039`、`+0.0048`、`-0.0018`，但交易/订单数分别增加 `+7`、`+11`、`+8`。这正是 R048 明确禁止的“仅压缩成交金额、却增加交易笔数”路径。三个场景的 `rejected_order_count` 均为 0；`max_pending_intent_count` 与基线相同为 4，因此失败由交易频率而非拒单或 pending 解释。

## 产物可追溯性

- 标准化指标：`platform/reports/experiments/r048_training_domestic_default/20260711_142633/metrics.json`、`platform/reports/experiments/r048_training_domestic_stress/20260711_142635/metrics.json`、`platform/reports/experiments/r048_training_domestic_dynamic_participation/20260711_142637/metrics.json`。
- 原始候选与基线 artifacts：`platform/results/backtests/r048_training_domestic_{default,stress,dynamic_participation}/` 下对应时间戳目录，含 `nav.csv`、`positions.csv`、`orders.csv`、`trades.csv`、`skipped_orders.csv`、`manifest.json` 和 checkpoint。

## 后续动作

本预注册候选不进入冻结，不运行最终测试，也不保留在 `BUILTIN_STRATEGIES`。如需探索不同复位比例、冷却期或资产级规则，应创建新的研究课题并在首次训练前另行预注册，不能修改 R048。
