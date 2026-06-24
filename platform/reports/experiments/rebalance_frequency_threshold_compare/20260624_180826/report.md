# 每日调仓+5%阈值 vs 月度调仓对比报告

## 目标与假设
- 目标：研究 `platform/configs/` 下非 `generated/` 的活动 YAML 配置，在训练样本内使用 `daily + rebalance_threshold=0.05` 与 `monthly + rebalance_threshold=0.05` 两种调仓设置时的表现差异。
- 假设：每日检测并使用 5% 偏离阈值可能降低目标权重漂移，但也可能增加订单、成交和年化换手。
- 样本隔离：所有回测 `end_date` 均截断到 `2025-06-30`；未使用 `2025-07-01` 之后的最终测试样本。

## 执行口径
- 数据新鲜度：涉及资产本地最新日期均为 `2026-06-24`，满足当前日期 `2026-06-24` 的 7 日规则。
- 配置范围：只扫描 `platform/configs/*.yaml`，不进入 `platform/configs/generated/`。
- 跳过规则：跳过没有 `rebalance_threshold` 语义的 `monthly_equal_weight`；跳过训练样本共同历史到 `2025-06-30` 不满 3 年的配置。
- 临时调整：未改源代码。对 `adaptive_risk_deviation_volatility_triggered` 仅在运行配置中设 `min_threshold=max_threshold=rebalance_threshold=0.05` 且 `threshold_sensitivity=0.0`，使其固定使用 5% 阈值。
- 最终测试：未运行。本报告是训练样本内横截面对比，不作为候选策略提交或成功声明。

## 文件与命令
- 原始结果目录：`D:\strategy\platform\results\rebalance_frequency_threshold_compare\20260624_180826`
- 标准化汇总：`D:\strategy\platform\reports\experiments\rebalance_frequency_threshold_compare\20260624_180826\metrics.json`
- CSV 汇总：`D:\strategy\platform\reports\experiments\rebalance_frequency_threshold_compare\20260624_180826\summary.csv`
- 执行命令：`@' ...batch runner... '@ | .\env\python.exe -`，工作目录 `D:\strategy`；完整运行产物路径见 `metrics.json` 和 `summary.csv`。
- 源代码改动：无。

## 覆盖情况
- 成功完成双边回测配置数：24
- 回测失败配置数：0
- 跳过配置数：5

### 跳过配置
- `baseline_r0_domestic_equal_weight.yaml`：monthly_equal_weight 强制月末等权，没有 rebalance_threshold 语义
- `baseline_r1_user_holdings.yaml`：训练样本共同历史不足 3 年：common_start=2023-12-14, common_end=2025-06-30, days=371
- `baseline_r2_user_holdings.yaml`：训练样本共同历史不足 3 年：common_start=2023-12-14, common_end=2025-06-30, days=371
- `baseline_r3_user_holdings.yaml`：训练样本共同历史不足 3 年：common_start=2023-12-14, common_end=2025-06-30, days=371
- `baseline_r7_cluster_representative_damped.yaml`：训练样本共同历史不足 3 年：common_start=2024-03-28, common_end=2025-06-30, days=303

## 总体结论
- 在 24 个成功配置中，每日+5% 的 Sharpe 高于月度的有 5 个，年化收益更高的有 2 个，最大回撤更浅的有 6 个，年化金额换手更高的有 21 个。
- 平均差值（每日减月度）：Sharpe `-0.0489`，年化收益 `-0.53%`，年化金额换手 `8.65%`。
- 整体看，月度调仓在大多数配置上的 Sharpe 和年化收益更稳；每日+5% 在少数配置上改善 Sharpe，但通常伴随更高换手和更多成交/订单。
- 由于未做完整起始日期敏感性和最终测试样本验证，结论仅用于研究筛选。

## 配置明细
| 配置 | 策略 | 年化收益 日/月 | Sharpe 日/月 | 最大回撤 日/月 | 年化换手 日/月 | 成交笔数 日/月 | 拒单 日/月 | 结论 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `baseline_r2_global_ewma.yaml` | `risk_parity_lw_cov` | 14.59% / 15.06% | 1.3766 / 1.2231 | -10.59% / -13.27% | 80.29% / 65.23% | 352 / 194 | 510 / 419 | 每日 Sharpe 较高，但收益或换手代价需复核 |
| `baseline_r2_global_dividend_ewma.yaml` | `risk_parity_lw_cov` | 15.95% / 15.74% | 1.3560 / 1.2403 | -14.04% / -16.19% | 80.97% / 59.71% | 318 / 158 | 476 / 255 | 每日较优，需补充敏感性 |
| `baseline_r1_domestic_rolling.yaml` | `risk_parity` | 14.03% / 14.52% | 1.2751 / 1.2205 | -14.89% / -16.45% | 31.77% / 30.70% | 120 / 81 | 184 / 153 | 每日 Sharpe 较高，但收益或换手代价需复核 |
| `r1_domestic_rolling_30y_bond_futures.yaml` | `risk_parity` | 14.03% / 14.52% | 1.2751 / 1.2205 | -14.89% / -16.45% | 31.77% / 30.70% | 120 / 81 | 184 / 153 | 每日 Sharpe 较高，但收益或换手代价需复核 |
| `us_blend_ewma_risk_parity_cvar_dynamic_budget.yaml` | `risk_parity_cvar_dynamic_budget` | 14.96% / 15.08% | 0.6979 / 0.6773 | -29.00% / -31.50% | 58.72% / 51.34% | 305 / 178 | 390 / 347 | 差异有限/需复核 |
| `baseline_risk_parity_gerber.yaml` | `risk_parity_gerber` | 11.86% / 12.10% | 1.7960 / 1.8038 | -8.06% / -7.77% | 37.00% / 30.29% | 145 / 83 | 342 / 510 | 差异有限/需复核 |
| `baseline_risk_parity_hrp.yaml` | `hrp` | 13.21% / 13.66% | 2.1213 / 2.1331 | -7.45% / -7.00% | 67.45% / 55.99% | 262 / 151 | 530 / 486 | 差异有限/需复核 |
| `demo_r1_domestic_ewma_cov.yaml` | `risk_parity_ewma_cov` | 7.26% / 7.31% | 1.0186 / 1.0320 | -10.66% / -10.72% | 33.11% / 22.87% | 109 / 58 | 266 / 266 | 差异有限/需复核 |
| `baseline_us_blend_ewma.yaml` | `risk_parity_lw_cov` | 15.27% / 15.62% | 0.8101 / 0.8292 | -26.62% / -26.15% | 83.65% / 68.47% | 441 / 234 | 472 / 398 | 差异有限/需复核 |
| `r0_domestic_equal_weight_risk_parity_ewma.yaml` | `risk_parity_ewma` | 12.06% / 12.74% | 1.8633 / 1.8880 | -7.90% / -7.51% | 68.60% / 57.14% | 242 / 145 | 388 / 436 | 差异有限/需复核 |
| `baseline_risk_parity_lw_cov.yaml` | `risk_parity_lw_cov` | 11.82% / 12.28% | 1.8023 / 1.8347 | -7.77% / -7.59% | 33.10% / 33.44% | 128 / 98 | 524 / 475 | 差异有限/需复核 |
| `risk_parity_gerber_risk_parity_lw_cov.yaml` | `risk_parity_lw_cov` | 11.82% / 12.28% | 1.8023 / 1.8347 | -7.77% / -7.59% | 33.10% / 33.44% | 128 / 98 | 524 / 475 | 差异有限/需复核 |
| `r1_domestic_rolling_10y_bond_3x_vol.yaml` | `risk_parity` | 13.98% / 13.94% | 0.9212 / 0.9538 | -21.66% / -20.41% | 37.92% / 32.12% | 128 / 74 | 232 / 206 | 差异有限/需复核 |
| `baseline_r6_adaptive_risk_deviation.yaml` | `adaptive_risk_deviation_volatility_triggered` | 11.82% / 12.30% | 1.8023 / 1.8384 | -7.77% / -7.59% | 33.10% / 33.39% | 128 / 97 | 524 / 462 | 差异有限/需复核 |
| `baseline_r5_cvar_dynamic_budget.yaml` | `risk_parity_cvar_dynamic_budget` | 12.40% / 12.99% | 1.9796 / 2.0245 | -7.65% / -7.13% | 56.30% / 50.35% | 227 / 138 | 570 / 296 | 差异有限/需复核 |
| `baseline_r1_domestic_low_vol_ewma.yaml` | `risk_parity_ewma` | 16.13% / 16.59% | 1.6396 / 1.6956 | -12.30% / -11.98% | 76.50% / 57.30% | 221 / 125 | 274 / 401 | 月度较优 |
| `r3_global_nasdaq_all_weather_ewma_risk_parity_cvar_dynamic_budget.yaml` | `risk_parity_cvar_dynamic_budget` | 14.44% / 15.57% | 2.4824 / 2.5634 | -5.02% / -4.53% | 76.62% / 63.44% | 196 / 100 | 270 / 221 | 月度较优 |
| `r2_global_dividend_ewma_risk_parity_cvar_dynamic_budget.yaml` | `risk_parity_cvar_dynamic_budget` | 15.08% / 15.39% | 1.3294 / 1.4160 | -12.67% / -12.12% | 52.06% / 49.65% | 212 / 130 | 505 / 376 | 月度较优 |
| `r2_global_ewma_risk_parity_cvar_dynamic_budget.yaml` | `risk_parity_cvar_dynamic_budget` | 14.46% / 15.09% | 1.2735 / 1.4016 | -13.23% / -12.29% | 55.40% / 52.22% | 240 / 173 | 348 / 315 | 月度较优 |
| `r1_domestic_ewma_10y_bond_3x_vol.yaml` | `risk_parity_ewma` | 13.56% / 14.08% | 0.9848 / 1.1227 | -19.59% / -16.56% | 70.78% / 60.29% | 245 / 138 | 327 / 317 | 月度较优 |
| `baseline_r1_domestic_ewma.yaml` | `risk_parity_ewma` | 14.10% / 15.06% | 1.4362 / 1.6024 | -11.86% / -10.21% | 75.13% / 56.78% | 280 / 139 | 413 / 267 | 月度较优 |
| `r1_domestic_ewma_30y_bond_futures.yaml` | `risk_parity_ewma` | 14.10% / 15.06% | 1.4362 / 1.6024 | -11.86% / -10.21% | 75.13% / 56.78% | 280 / 139 | 413 / 267 | 月度较优 |
| `baseline_r3_global_nasdaq_all_weather_ewma.yaml` | `risk_parity_lw_cov` | 13.56% / 15.32% | 2.1334 / 2.3334 | -5.53% / -5.38% | 97.60% / 93.32% | 263 / 179 | 332 / 298 | 月度较优 |
| `r1_domestic_ewma_risk_parity_cvar_dynamic_budget.yaml` | `risk_parity_cvar_dynamic_budget` | 14.71% / 15.59% | 1.4144 / 1.7104 | -13.89% / -10.99% | 54.14% / 47.57% | 216 / 135 | 436 / 249 | 月度较优 |

## 建议
- 不建议直接把每日+5% 作为全局默认：它平均 Sharpe 低于月度，且平均年化换手更高。
- 可优先复查 `baseline_r2_global_dividend_ewma.yaml` 这类 Sharpe 和年化收益同时改善的配置，但其换手增幅明显，需按规则补做敏感性和最终样本验证。
- 对月度明显更优或每日换手显著上升的配置，保持月度调仓更稳妥。

## 未完成的验证
- 未运行每两个月一个起始日的完整敏感性矩阵；因此本报告不声明任何候选配置通过研究验证。
- 未运行 `2025-07-01` 之后的最终测试样本。
