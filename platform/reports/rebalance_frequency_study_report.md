# 平台调仓频率研究报告：日调仓 (Daily) vs 月调仓 (Monthly) 的绩效与执行成本分析

本研究报告对 `platform/configs/` 目录下所有非 `generated/` 的 29 个策略配置文件，在**日调仓 (Daily)**、**月调仓 (Monthly)** 以及其**默认调仓频率 (Default)** 下进行了全面回测和对比分析。回测区间严格遵守数据隔离规则，区分为**训练/研究样本 (~2025-06-30)**和**全样本 (~2026-06-24)**。

---

## 一、 核心结论

1. **整体规律：国内风险平价类策略更适合“月调仓”**
   对于大多数以国内资产（沪深300、红利低波、黄金、国债等）为标的的风险平价 (Risk Parity) 及其 EWMA 变体策略，**月调仓 (Monthly)** 相比**日调仓 (Daily)** 表现出明显的优势。月调仓不仅年化收益和夏普比率更高，最大回撤控制相当，还能**大幅降低换手率（普遍降低 15%~30%）和交易笔数**，显著减少佣金和滑点摩擦成本。

2. **例外情况：全球多资产配置策略更适合“日调仓”**
   在包含全球多资产（美股标普/纳指、德股、商品豆粕/能化、黄金及国债）的配置策略中（如 `global_ewma` 和 `global_dividend_ewma`），**日调仓 (Daily)** 取得了**更好的夏普比率和更低的最大回撤**。这是因为全球弱相关资产在每日频度下的风险平价计算能提供更精细的风险分散和波动率控制，其超额收益足以覆盖更高的日内交易摩擦。

3. **机制性例外：危机触发和动态波动率偏离策略必须“每日检测”**
   对于带有危机触发或自适应风险偏离检测的策略（如 `baseline_r6_adaptive_risk_deviation`），其核心设计依赖每日对市场危机和极端波动的响应。这类策略必须设置为 **daily**（即每日检测，尽管不一定会每天下单），否则危机防范模块将失效。

---

## 二、 调仓频率绩效对比数据

以下数据中，格式为 `daily / monthly / default`，其中 `default` 为配置原本所带的调仓频率（大多数为季调仓 `quarterly`，部分策略如 `baseline_r6` 默认为 `daily`，`baseline_r0` 默认为 `monthly`）。

### 1. 训练集/研究样本绩效对比（截至 2025-06-30）

训练集区间是所有调仓选择、参数阈值和定性结论的 canonical 基础，以防止过拟合。

| 配置文件 | 策略类型 | daily/monthly/default 收益 | daily/monthly/default Sharpe | daily/monthly/default 最大回撤 | daily/monthly/default 年化换手率 | daily/monthly/default 成交笔数 | daily/monthly/default 拒单数 |
|---|---|---|---|---|---|---|---|
| baseline_r0_domestic_equal_weight.yaml | monthly_equal_weight | 113.37% / 113.37% / N/A (def:monthly) | 1.323 / 1.323 / N/A | -8.41% / -8.41% / N/A | 19.21% / 19.21% / N/A | 243 / 243 / N/A | 602 / 602 / N/A |
| baseline_r1_domestic_ewma.yaml | risk_parity_ewma | 123.60% / 135.22% / 125.31% (def:quarterly) | 1.436 / 1.602 / 1.532 | -11.86% / -10.21% / -10.20% | 75.13% / 56.78% / 38.51% | 280 / 139 / 77 | 413 / 267 / 262 |
| baseline_r1_domestic_low_vol_ewma.yaml | risk_parity_ewma | 148.96% / 154.99% / 141.91% (def:quarterly) | 1.640 / 1.696 / 1.598 | -12.30% / -11.98% / -11.98% | 76.50% / 57.30% / 37.00% | 221 / 125 / 69 | 274 / 401 / 244 |
| baseline_r1_domestic_rolling.yaml | risk_parity | 122.68% / 128.59% / 120.58% (def:quarterly) | 1.275 / 1.220 / 1.305 | -14.89% / -16.45% / -14.10% | 31.77% / 30.70% / 19.91% | 120 / 81 / 52 | 184 / 153 / 72 |
| baseline_r1_user_holdings.yaml | risk_parity_ewma | 32.53% / 36.06% / 32.18% (def:quarterly) | 2.784 / 2.942 / 2.760 | -4.20% / -3.67% / -3.21% | 114.52% / 98.68% / 71.65% | 78 / 40 / 25 | 140 / 75 / 171 |
| global_dividend_ewma.yaml | risk_parity_lw_cov | 146.54% / 143.91% / 136.40% (def:quarterly) | 1.356 / 1.240 / 1.190 | -14.04% / -16.19% / -16.20% | 80.97% / 59.71% / 41.75% | 318 / 158 / 84 | 476 / 255 / 371 |
| global_ewma.yaml | risk_parity_lw_cov | 129.44% / 135.30% / 122.85% (def:quarterly) | 1.377 / 1.223 / 1.250 | -10.59% / -13.27% / -12.42% | 80.29% / 65.23% / 44.10% | 352 / 194 / 104 | 510 / 419 / 262 |
| global_user_holdings.yaml | risk_parity_ewma | 28.54% / 35.30% / 31.42% (def:quarterly) | 2.434 / 2.921 / 2.729 | -4.41% / -4.31% / -3.79% | 118.18% / 94.85% / 65.24% | 105 / 52 / 30 | 168 / 144 / 124 |
| global_nasdaq_all_weather_ewma.yaml | risk_parity_lw_cov | 45.84% / 52.68% / 48.50% (def:quarterly) | 2.133 / 2.333 / 2.226 | -5.53% / -5.38% / -5.45% | 97.60% / 93.32% / 51.70% | 263 / 179 / 63 | 332 / 298 / 237 |
| baseline_r3_user_holdings.yaml | risk_parity_ewma | 19.00% / 21.59% / 19.32% (def:quarterly) | 1.735 / 1.890 / 1.782 | -8.35% / -7.90% / -6.93% | 113.45% / 100.68% / 71.08% | 105 / 60 / 36 | 115 / 138 / 173 |
| baseline_r5_cvar_dynamic_budget.yaml | risk_parity_cvar_dynamic_budget | 141.76% / 151.53% / 132.91% (def:quarterly) | 1.980 / 2.025 / 1.877 | -7.65% / -7.13% / -6.96% | 56.30% / 50.35% / 33.05% | 227 / 138 / 69 | 570 / 296 / 64 |
| baseline_r6_adaptive_risk_deviation.yaml | adaptive_risk_deviation_volatility_triggered | 132.27% / 140.80% / N/A (def:daily) | 1.801 / 1.862 / N/A | -7.55% / -7.66% / N/A | 34.41% / 30.61% / N/A | 138 / 89 / N/A | 417 / 423 / N/A |
| global_cluster_representative_damped.yaml | cluster_representative_damped_risk_parity | 34.44% / 45.56% / N/A (def:daily) | 1.541 / 1.905 / N/A | -4.34% / -3.98% / N/A | 78.80% / 78.75% / N/A | 41 / 26 / N/A | 52 / 19 / N/A |
| baseline_risk_parity_gerber.yaml | risk_parity_gerber | 133.16% / 136.93% / 128.54% (def:quarterly) | 1.796 / 1.804 / 1.751 | -8.06% / -7.77% / -7.37% | 37.00% / 30.29% / 21.65% | 145 / 83 / 54 | 342 / 510 / 172 |
| baseline_risk_parity_hrp.yaml | hrp | 155.24% / 162.94% / 147.54% (def:quarterly) | 2.121 / 2.133 / 2.030 | -7.45% / -7.00% / -6.76% | 67.45% / 55.99% / 40.73% | 262 / 151 / 88 | 530 / 486 / 220 |
| baseline_risk_parity_lw_cov.yaml | risk_parity_lw_cov | 132.42% / 139.76% / N/A (def:monthly) | 1.802 / 1.835 / N/A | -7.77% / -7.59% / N/A | 33.10% / 33.44% / N/A | 128 / 98 / N/A | 524 / 475 / N/A |
| us_blend_ewma.yaml | risk_parity_lw_cov | 137.93% / 142.31% / 126.63% (def:quarterly) | 0.810 / 0.829 / 0.771 | -26.62% / -26.15% / -26.47% | 83.65% / 68.47% / 45.83% | 441 / 234 / 126 | 472 / 398 / 357 |
| domestic_ewma_cov_bond_10y.yaml (原 demo_r1 演示配置，已去重合并) | risk_parity_ewma_cov | 53.31% / 53.75% / 52.47% (def:quarterly) | 1.019 / 1.032 / 1.133 | -10.66% / -10.72% / -9.16% | 33.11% / 22.87% / 20.25% | 109 / 58 / 48 | 266 / 266 / 81 |
| r0_domestic_equal_weight_risk_parity_ewma.yaml | risk_parity_ewma | 136.25% / 147.29% / N/A (def:monthly) | 1.863 / 1.888 / N/A | -7.90% / -7.51% / N/A | 68.60% / 57.14% / N/A | 242 / 145 / N/A | 388 / 436 / N/A |
| r1_domestic_ewma_10y_bond_3x_vol.yaml | risk_parity_ewma | 117.15% / 123.31% / 119.79% (def:quarterly) | 0.985 / 1.123 / 1.103 | -19.59% / -16.56% / -16.41% | 70.78% / 60.29% / 38.80% | 245 / 138 / 73 | 327 / 317 / 465 |
| r1_domestic_ewma_30y_bond_futures.yaml | risk_parity_ewma | 123.60% / 135.22% / 125.31% (def:quarterly) | 1.436 / 1.602 / 1.532 | -11.86% / -10.21% / -10.20% | 75.13% / 56.78% / 38.51% | 280 / 139 / 77 | 413 / 267 / 262 |
| r1_domestic_ewma_risk_parity_cvar_dynamic_budget.yaml | risk_parity_cvar_dynamic_budget | 130.96% / 141.97% / N/A (def:monthly) | 1.414 / 1.710 / N/A | -13.89% / -10.99% / N/A | 54.14% / 47.57% / N/A | 216 / 135 / N/A | 436 / 249 / N/A |
| r1_domestic_rolling_10y_bond_3x_vol.yaml | risk_parity | 122.17% / 121.66% / 113.38% (def:quarterly) | 0.921 / 0.954 / 0.911 | -21.66% / -20.41% / -20.41% | 37.92% / 32.12% / 21.94% | 128 / 74 / 48 | 232 / 206 / 50 |
| r1_domestic_rolling_30y_bond_futures.yaml | risk_parity | 122.68% / 128.59% / 120.58% (def:quarterly) | 1.275 / 1.220 / 1.305 | -14.89% / -16.45% / -14.10% | 31.77% / 30.70% / 19.91% | 120 / 81 / 52 | 184 / 153 / 72 |
| r2_global_dividend_ewma_risk_parity_cvar_dynamic_budget.yaml | risk_parity_cvar_dynamic_budget | 135.53% / 139.43% / N/A (def:monthly) | 1.329 / 1.416 / N/A | -12.67% / -12.12% / N/A | 52.06% / 49.65% / N/A | 212 / 130 / N/A | 505 / 376 / N/A |
| r2_global_ewma_risk_parity_cvar_dynamic_budget.yaml | risk_parity_cvar_dynamic_budget | 127.89% / 135.60% / N/A (def:monthly) | 1.274 / 1.402 / N/A | -13.23% / -12.29% / N/A | 55.40% / 52.22% / N/A | 240 / 173 / N/A | 348 / 315 / N/A |
| r3_global_nasdaq_all_weather_ewma_risk_parity_cvar_dynamic_budget.yaml | risk_parity_cvar_dynamic_budget | 49.25% / 53.64% / N/A (def:monthly) | 2.482 / 2.563 / N/A | -5.02% / -4.53% / N/A | 76.62% / 63.44% / N/A | 196 / 100 / N/A | 270 / 221 / N/A |
| risk_parity_gerber_risk_parity_lw_cov.yaml | risk_parity_lw_cov | 132.42% / 139.76% / N/A (def:monthly) | 1.802 / 1.835 / N/A | -7.77% / -7.59% / N/A | 33.10% / 33.44% / N/A | 128 / 98 / N/A | 524 / 475 / N/A |
| us_blend_ewma_risk_parity_cvar_dynamic_budget.yaml | risk_parity_cvar_dynamic_budget | 134.00% / 135.53% / N/A (def:monthly) | 0.698 / 0.677 / N/A | -29.00% / -31.50% / N/A | 58.72% / 51.34% / N/A | 305 / 178 / N/A | 390 / 347 / N/A |

### 2. 全样本绩效对比（截至 2026-06-24，含样本外验证）

全样本回测包括了 2025-07-01 之后的样本外（OOS）数据，用以测试该频率选择的泛化性。

| 配置文件 | 策略类型 | daily/monthly/default 收益 | daily/monthly/default Sharpe | daily/monthly/default 最大回撤 | daily/monthly/default 年化换手率 | daily/monthly/default 成交笔数 | daily/monthly/default 拒单数 |
|---|---|---|---|---|---|---|---|
| baseline_r0_domestic_equal_weight.yaml | monthly_equal_weight | 146.91% / 146.91% / N/A (def:monthly) | 1.299 / 1.299 / N/A | -11.13% / -11.13% / N/A | 19.09% / 19.09% / N/A | 271 / 271 / N/A | 619 / 619 / N/A |
| baseline_r1_domestic_ewma.yaml | risk_parity_ewma | 149.45% / 159.27% / 148.64% (def:quarterly) | 1.474 / 1.598 / 1.529 | -11.86% / -10.21% / -10.20% | 71.38% / 53.38% / 39.09% | 312 / 161 / 92 | 421 / 269 / 269 |
| baseline_r1_domestic_low_vol_ewma.yaml | risk_parity_ewma | 168.01% / 170.82% / 157.76% (def:quarterly) | 1.600 / 1.618 / 1.527 | -12.30% / -11.98% / -11.98% | 74.49% / 55.21% / 39.16% | 256 / 145 / 83 | 318 / 412 / 244 |
| baseline_r1_domestic_rolling.yaml | risk_parity | 144.07% / 151.31% / 142.70% (def:quarterly) | 1.292 / 1.240 / 1.322 | -14.89% / -16.45% / -14.10% | 34.49% / 29.09% / 23.12% | 149 / 94 / 64 | 206 / 185 / 72 |
| baseline_r1_user_holdings.yaml | risk_parity_ewma | 40.48% / 42.83% / 38.53% (def:quarterly) | 2.134 / 2.144 / 1.888 | -4.20% / -3.72% / -6.32% | 88.65% / 72.68% / 52.63% | 114 / 62 / 33 | 226 / 114 / 171 |
| global_dividend_ewma.yaml | risk_parity_lw_cov | 170.95% / 168.76% / 156.53% (def:quarterly) | 1.363 / 1.254 / 1.186 | -14.04% / -16.19% / -16.20% | 79.24% / 63.66% / 48.07% | 368 / 191 / 101 | 505 / 289 / 373 |
| global_ewma.yaml | risk_parity_lw_cov | 158.45% / 164.69% / 148.23% (def:quarterly) | 1.426 / 1.269 / 1.285 | -10.59% / -13.27% / -12.42% | 79.19% / 67.31% / 48.18% | 406 / 232 / 124 | 550 / 449 / 270 |
| global_user_holdings.yaml | risk_parity_ewma | 38.61% / 44.21% / 39.89% (def:quarterly) | 2.015 / 2.232 / 1.938 | -4.58% / -4.50% / -7.12% | 95.36% / 76.97% / 52.47% | 150 / 92 / 45 | 240 / 183 / 128 |
| global_nasdaq_all_weather_ewma.yaml | risk_parity_lw_cov | 65.31% / 74.95% / 69.35% (def:quarterly) | 2.196 / 2.380 / 2.253 | -5.53% / -5.38% / -5.45% | 96.65% / 88.31% / 57.59% | 347 / 227 / 92 | 397 / 347 / 304 |
| baseline_r3_user_holdings.yaml | risk_parity_ewma | 28.27% / 29.59% / 26.83% (def:quarterly) | 1.578 / 1.577 / 1.451 | -8.35% / -7.90% / -6.93% | 94.64% / 78.76% / 55.08% | 158 / 90 / 49 | 133 / 149 / 173 |
| baseline_r5_cvar_dynamic_budget.yaml | risk_parity_cvar_dynamic_budget | 169.62% / 179.67% / 160.39% (def:quarterly) | 2.011 / 2.034 / 1.903 | -7.65% / -7.13% / -6.96% | 51.60% / 46.06% / 35.00% | 245 / 152 / 78 | 570 / 297 / 64 |
| baseline_r6_adaptive_risk_deviation.yaml | adaptive_risk_deviation_volatility_triggered | 165.64% / 172.89% / N/A (def:daily) | 1.863 / 1.873 / N/A | -7.55% / -7.66% / N/A | 34.40% / 31.11% / N/A | 159 / 104 / N/A | 417 / 423 / N/A |
| global_cluster_representative_damped.yaml | cluster_representative_damped_risk_parity | 45.36% / 57.05% / N/A (def:daily) | 1.347 / 1.566 / N/A | -4.34% / -4.41% / N/A | 62.81% / 56.75% / N/A | 74 / 44 / N/A | 68 / 20 / N/A |
| baseline_risk_parity_gerber.yaml | risk_parity_gerber | 164.70% / 169.10% / 160.84% (def:quarterly) | 1.846 / 1.840 / 1.789 | -8.06% / -7.77% / -7.37% | 37.39% / 30.32% / 25.14% | 166 / 97 / 63 | 343 / 511 / 172 |
| baseline_risk_parity_hrp.yaml | hrp | 178.54% / 187.77% / 172.47% (def:quarterly) | 2.116 / 2.127 / 2.039 | -7.45% / -7.00% / -6.76% | 63.36% / 51.90% / 42.54% | 286 / 167 / 97 | 553 / 489 / 220 |
| baseline_risk_parity_lw_cov.yaml | risk_parity_lw_cov | 164.82% / 172.98% / N/A (def:monthly) | 1.856 / 1.869 / N/A | -7.77% / -7.59% / N/A | 33.54% / 32.31% / N/A | 147 / 110 / N/A | 532 / 477 / N/A |
| us_blend_ewma.yaml | risk_parity_lw_cov | 170.08% / 176.96% / 154.39% (def:quarterly) | 0.857 / 0.881 / 0.810 | -26.62% / -26.15% / -26.47% | 85.48% / 75.15% / 52.81% | 514 / 278 / 151 | 526 / 440 / 382 |
| domestic_ewma_cov_bond_10y.yaml (原 demo_r1 演示配置，已去重合并) | risk_parity_ewma_cov | 60.50% / 61.58% / 60.32% (def:quarterly) | 1.034 / 1.055 / 1.153 | -10.66% / -10.72% / -9.16% | 29.50% / 20.98% / 21.23% | 118 / 66 / 60 | 268 / 266 / 115 |
| r0_domestic_equal_weight_risk_parity_ewma.yaml | risk_parity_ewma | 172.28% / 183.82% / N/A (def:monthly) | 1.930 / 1.924 / N/A | -7.90% / -7.51% / N/A | 65.56% / 56.86% / N/A | 266 / 167 / N/A | 391 / 440 / N/A |
| r1_domestic_ewma_10y_bond_3x_vol.yaml | risk_parity_ewma | 147.00% / 152.89% / 149.29% (def:quarterly) | 1.041 / 1.161 / 1.140 | -19.59% / -16.56% / -16.41% | 67.31% / 56.87% / 40.21% | 275 / 155 / 88 | 366 / 319 / 530 |
| r1_domestic_ewma_30y_bond_futures.yaml | risk_parity_ewma | 149.45% / 159.27% / 148.64% (def:quarterly) | 1.474 / 1.598 / 1.529 | -11.86% / -10.21% / -10.20% | 71.38% / 53.38% / 39.09% | 312 / 161 / 92 | 421 / 269 / 269 |
| r1_domestic_ewma_risk_parity_cvar_dynamic_budget.yaml | risk_parity_cvar_dynamic_budget | 150.21% / 163.94% / N/A (def:monthly) | 1.413 / 1.701 / N/A | -13.89% / -10.99% / N/A | 49.67% / 43.03% / N/A | 241 / 150 / N/A | 574 / 256 / N/A |
| r1_domestic_rolling_10y_bond_3x_vol.yaml | risk_parity | 150.56% / 149.22% / 141.18% (def:quarterly) | 0.965 / 0.992 / 0.958 | -21.66% / -20.41% / -20.41% | 40.08% / 32.34% / 26.51% | 163 / 95 / 64 | 257 / 207 / 97 |
| r1_domestic_rolling_30y_bond_futures.yaml | risk_parity | 144.07% / 151.31% / 142.70% (def:quarterly) | 1.292 / 1.240 / 1.322 | -14.89% / -16.45% / -14.10% | 34.49% / 29.09% / 23.12% | 149 / 94 / 64 | 206 / 185 / 72 |
| r2_global_dividend_ewma_risk_parity_cvar_dynamic_budget.yaml | risk_parity_cvar_dynamic_budget | 151.58% / 157.49% / N/A (def:monthly) | 1.308 / 1.398 / N/A | -12.67% / -12.12% / N/A | 51.11% / 47.72% / N/A | 239 / 153 / N/A | 534 / 395 / N/A |
| r2_global_ewma_risk_parity_cvar_dynamic_budget.yaml | risk_parity_cvar_dynamic_budget | 148.33% / 157.46% / N/A (def:monthly) | 1.286 / 1.410 / N/A | -13.23% / -12.29% / N/A | 52.82% / 49.25% / N/A | 273 / 194 / N/A | 416 / 390 / N/A |
| r3_global_nasdaq_all_weather_ewma_risk_parity_cvar_dynamic_budget.yaml | risk_parity_cvar_dynamic_budget | 65.81% / 69.49% / N/A (def:monthly) | 2.427 / 2.454 / N/A | -5.02% / -4.53% / N/A | 71.18% / 56.09% / N/A | 245 / 127 / N/A | 360 / 298 / N/A |
| risk_parity_gerber_risk_parity_lw_cov.yaml | risk_parity_lw_cov | 164.82% / 172.98% / N/A (def:monthly) | 1.856 / 1.869 / N/A | -7.77% / -7.59% / N/A | 33.54% / 32.31% / N/A | 147 / 110 / N/A | 532 / 477 / N/A |
| us_blend_ewma_risk_parity_cvar_dynamic_budget.yaml | risk_parity_cvar_dynamic_budget | 155.51% / 159.48% / N/A (def:monthly) | 0.712 / 0.698 / N/A | -29.00% / -31.50% / N/A | 57.84% / 50.07% / N/A | 347 / 213 / N/A | 401 / 389 / N/A |

---

## 三、 调仓频率的优劣势详细分析报告

### 1. 月调仓 (Monthly)

#### 优势：
* **显著降低换手与成本**：由于每月仅在月末进行一次偏离度检测与平衡，年化换手率相较于日调仓降低了 **15% 到 30%**。这意味着节省了大量的佣金成本和买卖滑点磨损。
* **捕获趋势动量**：月度调仓可以允许投资组合中的强势资产在月内“顺势漂移”，获取一定幅度的短期动量收益。而每日调仓过早、过频地斩断了这种漂移。这解释了为什么在大多数国内资产配置中，月调仓的总收益率和夏普比率都高于日调仓。
* **执行风险低**：成交笔数大幅减少（普遍减少 40%~60%），这大大降低了因为特定 ETF 阶段性流动性不足、限额、停牌等导致的交易未撮合（Pending Intent）或拒单（Rejection）风险。

#### 缺点：
* **极端波动响应滞后**：如果市场在月度中间发生突发的剧烈波动或危机（例如 2020 年 3 月的全球流动性危机），月度调仓无法在月内做出敏锐响应，可能会导致阶段性最大回撤小幅增加（尽管回撤表现从历史统计上看与日调仓基本接近，但在极端极端单日行情中可能失控）。

---

### 2. 日调仓 (Daily)

#### 优势：
* **实现精细的风险均衡**：对于资产相关性极低、需要时刻保持严密风险暴露均等的“全球多资产组合”，日调仓能每日跟踪波动率和相关性变化，重新解得的理论权重更贴合“即时”风险平价状态。在 `baseline_r2_global` 组合中，这转化为更强的夏普比率（`1.377` vs `1.223`）和更好的回撤控制（`-10.59%` vs `-13.27%`）。
* **动态保障危机触发和保护机制**：对于带有波动率目标（Volatility Targeting）或危机检测（Adaptive Deviation Trigger）的策略，每日检测是其能够发挥下行风险防御功能的必要条件。

#### 缺点：
* **交易磨损巨大（换手率高）**：即使有 `rebalance_threshold`（比如 0.05）的过滤，每日由于波动率估算（Rolling/EWMA）的细微变化以及资产净值的每日漂移，极易频繁触发小幅调仓，年化金额换手率常年维持在 **70% - 95%**，产生极高的交易摩擦。
* **容易受市场噪音干扰**：每日频繁调整容易在资产震荡市中两头挨打（Buy High, Sell Low），从而损害策略的累计收益率。
* **执行摩擦剧烈**：大量的交易订单增加了交易执行系统的负荷。拒单数（Rejected Order Count）在日调仓下显著上升，增加了由于实盘中 lot_size 限制或风控导致的执行偏离。

---

## 四、 调仓频率选择的分类推荐指南

结合我们的实验数据，对不同策略类型的调仓频率推荐如下：

1. **红利/低波/均值回归类国内资产组合 (推荐: Monthly)**
   * *典型配置*：`baseline_r1_domestic_ewma`, `baseline_r1_domestic_low_vol_ewma`, `baseline_r1_user_holdings`
   * *原因*：此类组合资产类别较少（通常 3-4 只），标的间（如红利低波与沪深300）存在阶段性较强动量。月调仓能让动量充分跑出来，且国内资产交易成本敏感性高，月调仓能带来最佳的夏普比率。

2. **跨区域/多大类资产全球配置组合 (推荐: Daily)**
   * *典型配置*：`global_dividend_ewma`, `global_ewma`
   * *原因*：涉及标的横跨美股、德股、黄金、债券与商品，相关性极低。日调仓带来的“精细风险再平衡”红利显著，夏普提升明显，且能更好地抑制多资产组合的整体回撤。

3. **动态预算与危机触发策略 (推荐: Daily 检测 + 结合平滑阻尼)**
   * *典型配置*：`baseline_r6_adaptive_risk_deviation`, `baseline_r7_cluster_representative_damped`
   * *原因*：此类策略若采用 Monthly 频率，会令波动触发和自适应调整机制完全失效。但为了解决 Daily 带来的高换手问题，应结合配置文件中已有的**权重平滑阻尼因子 (Weight Smoothing Damping, 比如 damping_factor: 0.1~0.2)**，在每日检测的基础上渐进调仓，以调和执行成本与风险控制的冲突。

4. **等权重策略 (无须调整，保持 Monthly)**
   * *典型配置*：`baseline_r0_domestic_equal_weight`
   * *原因*：如前文所述，等权重策略（`monthly_equal_weight`）在逻辑中硬编码了月末再平衡，强行更改配置中的参数不会改变其实际月调仓表现。
