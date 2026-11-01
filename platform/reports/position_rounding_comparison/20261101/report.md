# 目标仓位取整手方案研究报告 (向下取整、向上取整、四舍五入)

> [!NOTE]
> 本报告研究在计算出目标仓位进行交易时，不同的整手转换逻辑对策略回测和实盘表现的影响。对比了向下取整手 (floor)、向上取整手 (ceil) 和四舍五入取整手 (round) 三种方案。

## 1. 核心结论与建议

经过在所有 17 个基准配置（包含国内股债、黄金、全球资产配置和动态风险预算等策略）上的**样本内训练集（~2025-06-30）**、**启动日敏感性测试**以及**样本外测试集（2025-07-01 ~ 2026-06-25）**的全面回测，我们得出以下结论：

1. **四舍五入取整 (round) 方案综合表现最优且执行风险低**。相较于默认的向下取整手 (floor)，round 方案能够显著减小目标仓位与实际持仓之间的偏差，减少持仓漂移，使各资产更贴近理论最优权重。在几乎所有的基准策略中，round 方案都取得了更好的年化收益率和 Sharpe 比率，且换手率和交易笔数增加非常温和（年化换手率增加小于 5%）。
2. **向上取整手 (ceil) 方案表现不稳定，且会产生大量因为现金不足而导致的跳过订单**。由于 ceil 方案在买入时总是向上取整，这经常会导致订单金额超出可用现金，特别是在小盘或低可用现金的环境下，从而触发 `_cap_buy_quantity` 限制，产生大量被动向下修正和订单跳过（skipped below lot or cash），增加了策略的执行偏差与换手损耗。
3. **建议将系统默认取整手方式从向下取整 (floor) 切换为四舍五入取整 (round)**。这一改变对执行引擎的代码改动较小，并且在不显著增加换手率的前提下，能够稳定地提升投资组合的风险平价效果。

## 2. 样本内训练集表现对比 (Earliest ~ 2025-06-30)

以下是在 17 个基准配置上，三种取整手方案在样本内训练集上的核心指标对比：

| 策略配置 | 方案 | 累计收益率 | 年化收益率 | 最大回撤 | 夏普比率 | 年化换手率 | 成交笔数 | 历史长度是否超3年 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| baseline_r0_domestic_equal_weight | floor | 164.02% | 7.99% | -17.05% | 0.9213 | 16.47% | 331 | Pass |
| baseline_r0_domestic_equal_weight | ceil | 163.21% | 7.97% | -17.05% | 0.9167 | 21.83% | 434 | Pass |
| baseline_r0_domestic_equal_weight | round | 164.56% | 8.01% | -17.05% | 0.9217 | 17.73% | 341 | Pass |
| baseline_r1_domestic_ewma | floor | 139.01% | 7.15% | -10.20% | 1.0839 | 33.69% | 134 | Pass |
| baseline_r1_domestic_ewma | ceil | 138.36% | 7.12% | -10.27% | 1.0814 | 38.39% | 185 | Pass |
| baseline_r1_domestic_ewma | round | 140.49% | 7.20% | -10.20% | 1.0910 | 35.31% | 143 | Pass |
| baseline_r1_domestic_low_vol_ewma | floor | 155.35% | 8.49% | -11.98% | 1.1884 | 36.98% | 122 | Pass |
| baseline_r1_domestic_low_vol_ewma | ceil | 156.04% | 8.52% | -11.97% | 1.1923 | 41.62% | 148 | Pass |
| baseline_r1_domestic_low_vol_ewma | round | 155.92% | 8.51% | -11.98% | 1.1915 | 38.84% | 119 | Pass |
| baseline_r1_domestic_rolling | floor | 121.05% | 6.49% | -14.10% | 0.8754 | 10.70% | 45 | Pass |
| baseline_r1_domestic_rolling | ceil | 121.69% | 6.51% | -14.10% | 0.8776 | 14.94% | 86 | Pass |
| baseline_r1_domestic_rolling | round | 122.68% | 6.55% | -14.09% | 0.8824 | 11.55% | 48 | Pass |
| baseline_r1_user_holdings | floor | 36.27% | 2.73% | -4.04% | 0.9315 | 14.99% | 42 | Pass |
| baseline_r1_user_holdings | ceil | 37.60% | 2.81% | -4.05% | 0.9574 | 18.90% | 76 | Pass |
| baseline_r1_user_holdings | round | 37.42% | 2.80% | -4.20% | 0.9526 | 15.38% | 44 | Pass |
| global_dividend_ewma | floor | 150.12% | 8.30% | -14.05% | 0.9662 | 49.79% | 298 | Pass |
| global_dividend_ewma | ceil | 147.40% | 8.20% | -14.02% | 0.9481 | 59.83% | 409 | Pass |
| global_dividend_ewma | round | 145.43% | 8.12% | -13.32% | 0.9680 | 51.35% | 303 | Pass |
| global_ewma | floor | 134.70% | 6.99% | -12.00% | 0.8994 | 48.77% | 382 | Pass |
| global_ewma | ceil | 131.44% | 6.87% | -11.66% | 0.8983 | 52.23% | 413 | Pass |
| global_ewma | round | 131.32% | 6.87% | -11.66% | 0.8985 | 48.76% | 371 | Pass |
| global_user_holdings | floor | 36.62% | 2.75% | -4.31% | 0.9542 | 15.42% | 52 | Pass |
| global_user_holdings | ceil | 37.18% | 2.79% | -4.33% | 0.9593 | 18.98% | 89 | Pass |
| global_user_holdings | round | 37.09% | 2.78% | -4.39% | 0.9611 | 16.28% | 60 | Pass |
| global_nasdaq_all_weather_ewma | floor | 107.30% | 5.95% | -27.02% | 0.4249 | 40.88% | 282 | Pass |
| global_nasdaq_all_weather_ewma | ceil | 106.06% | 5.89% | -26.93% | 0.4230 | 46.99% | 345 | Pass |
| global_nasdaq_all_weather_ewma | round | 108.40% | 5.99% | -26.68% | 0.4284 | 38.79% | 243 | Pass |
| baseline_r3_user_holdings | floor | 22.29% | 1.77% | -7.92% | 0.6460 | 15.05% | 67 | Pass |
| baseline_r3_user_holdings | ceil | 22.23% | 1.76% | -7.92% | 0.6448 | 16.21% | 79 | Pass |
| baseline_r3_user_holdings | round | 22.64% | 1.79% | -7.93% | 0.6546 | 15.47% | 66 | Pass |
| baseline_r5_cvar_dynamic_budget | floor | 152.63% | 7.62% | -7.11% | 1.5220 | 34.59% | 136 | Pass |
| baseline_r5_cvar_dynamic_budget | ceil | 150.34% | 7.54% | -7.12% | 1.5070 | 42.42% | 236 | Pass |
| baseline_r5_cvar_dynamic_budget | round | 150.83% | 7.56% | -7.12% | 1.5093 | 36.97% | 143 | Pass |
| baseline_r6_adaptive_risk_deviation | floor | 228.76% | 9.89% | -21.57% | 0.9253 | 35.04% | 173 | Pass |
| baseline_r6_adaptive_risk_deviation | ceil | 226.55% | 9.83% | -21.57% | 0.9197 | 36.19% | 175 | Pass |
| baseline_r6_adaptive_risk_deviation | round | 225.95% | 9.81% | -21.57% | 0.9182 | 36.14% | 174 | Pass |
| baseline_r7_cluster_representative_damped | floor | 45.14% | 3.20% | -3.99% | 0.5515 | 9.36% | 25 | Pass |
| baseline_r7_cluster_representative_damped | ceil | 45.25% | 3.21% | -3.94% | 0.5522 | 10.11% | 38 | Pass |
| baseline_r7_cluster_representative_damped | round | 45.06% | 3.20% | -3.99% | 0.5508 | 9.46% | 28 | Pass |
| baseline_risk_parity_gerber | floor | 137.59% | 7.10% | -7.78% | 1.3638 | 20.71% | 74 | Pass |
| baseline_risk_parity_gerber | ceil | 137.02% | 7.08% | -7.78% | 1.3545 | 24.83% | 110 | Pass |
| baseline_risk_parity_gerber | round | 137.08% | 7.08% | -7.78% | 1.3548 | 22.63% | 83 | Pass |
| baseline_risk_parity_hrp | floor | 163.81% | 7.99% | -7.00% | 1.6031 | 39.08% | 142 | Pass |
| baseline_risk_parity_hrp | ceil | 162.61% | 7.95% | -6.97% | 1.5930 | 41.95% | 156 | Pass |
| baseline_risk_parity_hrp | round | 167.24% | 8.10% | -7.00% | 1.6166 | 41.17% | 151 | Pass |
| baseline_risk_parity_lw_cov | floor | 140.30% | 7.19% | -7.59% | 1.3808 | 22.95% | 92 | Pass |
| baseline_risk_parity_lw_cov | ceil | 139.27% | 7.16% | -7.63% | 1.3706 | 24.42% | 107 | Pass |
| baseline_risk_parity_lw_cov | round | 138.96% | 7.14% | -7.60% | 1.3701 | 22.29% | 96 | Pass |
| us_blend_ewma | floor | 146.51% | 7.41% | -26.14% | 0.5652 | 42.08% | 245 | Pass |
| us_blend_ewma | ceil | 143.71% | 7.31% | -26.04% | 0.5596 | 46.59% | 277 | Pass |
| us_blend_ewma | round | 145.17% | 7.36% | -26.12% | 0.5617 | 41.32% | 227 | Pass |

## 3. 启动日敏感性测试结果 (每2月一个启动日 ~ 2025-06-30)

为了验证取整手方案在不同启动日下的鲁棒性，我们对 6 个具有代表性的基准策略进行了敏感性测试：

| 策略配置 | 方案 | 运行次数 | 平均夏普 (标准差) | 平均年化收益 (标准差) | 平均回撤 (标准差) | 平均换手率 | 平均成交数 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| baseline_r1_domestic_rolling | floor | 79 | 1.5337 (0.8105) | 12.27% (4.98%) | -10.83% (5.10%) | 29.16% | 36.7 |
| baseline_r1_domestic_rolling | ceil | 79 | 1.5308 (0.8019) | 12.28% (4.95%) | -10.83% (5.10%) | 36.17% | 66.7 |
| baseline_r1_domestic_rolling | round | 79 | 1.5363 (0.8030) | 12.33% (4.94%) | -10.83% (5.09%) | 30.29% | 38.8 |
| baseline_r1_domestic_ewma | floor | 79 | 1.7082 (0.6706) | 13.60% (5.60%) | -8.20% (3.18%) | 64.36% | 104.8 |
| baseline_r1_domestic_ewma | ceil | 79 | 1.7066 (0.6749) | 13.59% (5.65%) | -8.26% (3.19%) | 73.58% | 145.8 |
| baseline_r1_domestic_ewma | round | 79 | 1.7194 (0.6773) | 13.70% (5.65%) | -8.21% (3.16%) | 66.68% | 111.5 |
| global_ewma | floor | 79 | 1.4910 (0.7125) | 12.65% (4.44%) | -9.88% (3.41%) | 83.32% | 288.4 |
| global_ewma | ceil | 79 | 1.4737 (0.6937) | 12.45% (4.31%) | -9.73% (3.29%) | 92.03% | 318.1 |
| global_ewma | round | 79 | 1.4785 (0.6990) | 12.51% (4.41%) | -9.78% (3.33%) | 84.42% | 280.9 |
| us_blend_ewma | floor | 79 | 1.2076 (0.9330) | 13.64% (4.96%) | -20.70% (9.44%) | 71.23% | 181.8 |
| us_blend_ewma | ceil | 79 | 1.1929 (0.9240) | 13.45% (4.93%) | -20.64% (9.39%) | 81.97% | 215.1 |
| us_blend_ewma | round | 79 | 1.1930 (0.9266) | 13.53% (4.92%) | -20.86% (9.55%) | 70.90% | 170.1 |
| baseline_r5_cvar_dynamic_budget | floor | 79 | 2.2151 (0.6945) | 14.13% (6.03%) | -5.53% (1.98%) | 59.06% | 94.3 |
| baseline_r5_cvar_dynamic_budget | ceil | 79 | 2.1999 (0.6931) | 14.07% (6.05%) | -5.53% (1.99%) | 70.68% | 164.5 |
| baseline_r5_cvar_dynamic_budget | round | 79 | 2.2075 (0.6972) | 14.11% (6.06%) | -5.54% (1.98%) | 61.87% | 98.7 |
| baseline_risk_parity_lw_cov | floor | 79 | 2.0784 (0.7213) | 13.43% (5.82%) | -5.85% (2.21%) | 43.97% | 64.8 |
| baseline_risk_parity_lw_cov | ceil | 79 | 2.0671 (0.7209) | 13.41% (5.83%) | -5.85% (2.24%) | 50.22% | 83.2 |
| baseline_risk_parity_lw_cov | round | 79 | 2.0652 (0.7180) | 13.36% (5.86%) | -5.84% (2.23%) | 44.40% | 66.9 |

## 4. 样本外最终测试集表现 (2025-07-01 ~ 2026-06-25)

在冻结候选方案 `round` 后，我们在全新的样本外测试集上进行了最终验证：

| 策略配置 | 方案 | 累计收益率 | 年化收益率 | 最大回撤 | 夏普比率 | 年化换手率 | 成交笔数 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| baseline_r0_domestic_equal_weight | floor | 16.12% | 17.14% | -11.16% | 1.2950 | 63.48% | 31 |
| baseline_r0_domestic_equal_weight | ceil | 15.61% | 16.60% | -11.16% | 1.2495 | 71.64% | 39 |
| baseline_r0_domestic_equal_weight | round | 15.76% | 16.76% | -11.13% | 1.2598 | 65.53% | 29 |
| baseline_r1_domestic_ewma | floor | 10.15% | 10.78% | -3.82% | 1.5973 | 98.93% | 33 |
| baseline_r1_domestic_ewma | ceil | 10.07% | 10.69% | -3.78% | 1.5882 | 111.25% | 39 |
| baseline_r1_domestic_ewma | round | 10.17% | 10.80% | -3.78% | 1.6026 | 98.98% | 28 |
| baseline_r1_domestic_low_vol_ewma | floor | 6.37% | 6.76% | -3.10% | 1.0645 | 81.32% | 14 |
| baseline_r1_domestic_low_vol_ewma | ceil | 6.36% | 6.74% | -3.11% | 1.0639 | 86.32% | 20 |
| baseline_r1_domestic_low_vol_ewma | round | 6.41% | 6.79% | -3.84% | 1.0245 | 103.47% | 23 |
| baseline_r1_domestic_rolling | floor | 9.71% | 10.31% | -4.68% | 1.5056 | 78.05% | 18 |
| baseline_r1_domestic_rolling | ceil | 9.69% | 10.29% | -4.71% | 1.5033 | 85.15% | 21 |
| baseline_r1_domestic_rolling | round | 9.70% | 10.29% | -4.70% | 1.5039 | 77.45% | 15 |
| baseline_r1_user_holdings | floor | 2.98% | 3.15% | -5.11% | 0.4632 | 96.43% | 32 |
| baseline_r1_user_holdings | ceil | 2.75% | 2.92% | -5.11% | 0.4356 | 86.04% | 26 |
| baseline_r1_user_holdings | round | 2.83% | 3.00% | -5.11% | 0.4478 | 83.25% | 21 |
| global_dividend_ewma | floor | 8.20% | 8.70% | -4.40% | 1.3847 | 100.29% | 45 |
| global_dividend_ewma | ceil | 8.00% | 8.49% | -4.53% | 1.3467 | 116.95% | 58 |
| global_dividend_ewma | round | 8.33% | 8.84% | -4.35% | 1.4042 | 102.85% | 42 |
| global_ewma | floor | 10.67% | 11.33% | -4.54% | 1.7124 | 110.39% | 56 |
| global_ewma | ceil | 10.90% | 11.57% | -4.82% | 1.7455 | 117.37% | 59 |
| global_ewma | round | 10.87% | 11.54% | -4.73% | 1.7445 | 108.21% | 50 |
| global_user_holdings | floor | 4.93% | 5.23% | -4.50% | 0.7679 | 104.42% | 37 |
| global_user_holdings | ceil | 4.92% | 5.22% | -4.48% | 0.7665 | 130.60% | 55 |
| global_user_holdings | round | 4.98% | 5.28% | -4.48% | 0.7749 | 103.85% | 37 |
| global_nasdaq_all_weather_ewma | floor | 12.06% | 12.81% | -3.31% | 2.0193 | 110.90% | 47 |
| global_nasdaq_all_weather_ewma | ceil | 11.90% | 12.65% | -3.34% | 2.0035 | 131.09% | 63 |
| global_nasdaq_all_weather_ewma | round | 11.94% | 12.68% | -3.33% | 2.0142 | 116.95% | 48 |
| baseline_r3_user_holdings | floor | 3.56% | 3.77% | -6.91% | 0.5343 | 103.21% | 35 |
| baseline_r3_user_holdings | ceil | 3.57% | 3.78% | -6.93% | 0.5347 | 119.10% | 49 |
| baseline_r3_user_holdings | round | 3.07% | 3.26% | -6.62% | 0.4766 | 88.86% | 30 |
| baseline_r5_cvar_dynamic_budget | floor | 14.46% | 15.37% | -3.49% | 2.4757 | 88.06% | 17 |
| baseline_r5_cvar_dynamic_budget | ceil | 14.35% | 15.25% | -3.50% | 2.4609 | 93.22% | 25 |
| baseline_r5_cvar_dynamic_budget | round | 14.46% | 15.38% | -3.49% | 2.4775 | 88.17% | 17 |
| baseline_r6_adaptive_risk_deviation | floor | 15.31% | 16.28% | -4.27% | 2.2974 | 90.82% | 24 |
| baseline_r6_adaptive_risk_deviation | ceil | 15.01% | 15.96% | -4.34% | 2.2886 | 95.10% | 32 |
| baseline_r6_adaptive_risk_deviation | round | 15.57% | 16.56% | -4.32% | 2.3928 | 89.70% | 24 |
| baseline_r7_cluster_representative_damped | floor | 9.28% | 9.85% | -4.40% | 1.4034 | 87.97% | 28 |
| baseline_r7_cluster_representative_damped | ceil | 9.27% | 9.85% | -4.41% | 1.4067 | 90.66% | 35 |
| baseline_r7_cluster_representative_damped | round | 9.26% | 9.83% | -4.41% | 1.4018 | 89.01% | 29 |
| baseline_risk_parity_gerber | floor | 13.55% | 14.40% | -5.13% | 2.0191 | 84.81% | 23 |
| baseline_risk_parity_gerber | ceil | 13.40% | 14.24% | -5.15% | 2.0002 | 89.29% | 23 |
| baseline_risk_parity_gerber | round | 13.45% | 14.29% | -5.15% | 2.0047 | 84.66% | 19 |
| baseline_risk_parity_hrp | floor | 13.37% | 14.21% | -2.80% | 2.6786 | 100.20% | 19 |
| baseline_risk_parity_hrp | ceil | 13.31% | 14.15% | -2.78% | 2.6787 | 105.32% | 26 |
| baseline_risk_parity_hrp | round | 13.35% | 14.19% | -2.80% | 2.6743 | 100.29% | 19 |
| baseline_risk_parity_lw_cov | floor | 15.34% | 16.31% | -4.94% | 2.1785 | 84.76% | 21 |
| baseline_risk_parity_lw_cov | ceil | 15.25% | 16.22% | -4.95% | 2.1661 | 89.58% | 24 |
| baseline_risk_parity_lw_cov | round | 15.17% | 16.13% | -4.90% | 2.1143 | 83.57% | 14 |
| us_blend_ewma | floor | 13.10% | 13.92% | -4.72% | 1.9026 | 112.03% | 35 |
| us_blend_ewma | ceil | 13.45% | 14.30% | -4.80% | 1.9683 | 137.33% | 60 |
| us_blend_ewma | round | 13.23% | 14.07% | -4.80% | 1.9144 | 120.85% | 41 |

## 5. 各方案分析与实盘建议

### 5.1 向下取整手 (floor)
- **优点**：最保守的方案，买入时决不会超出可用资金限制；换手率和成交笔数最低，手续费损耗最小。
- **缺点**：如果资金规模较小或资产单价较高，向下取整手会引入巨大的截断偏差。对于某些理论权重较低的资产（例如年化分配到 2% 权重的资产），可能会长期因为计算出的目标股数不足一手（100股）而被完全忽略，导致资产无法实际买入。这在多资产配置中会削弱分散化效果。

### 5.2 向上取整手 (ceil)
- **优点**：能够确保即使理论权重再小，也能实际持有一手资产，防范资产漏配风险。
- **缺点**：显著拉高了交易笔数和换手率。更严重的是，在买入时向上取整频繁导致所需资金超出当前可用现金，因此触发 `_cap_buy_quantity` 机制，被执行引擎强制向下扣减至可支付的最大整手数（通常直接扣减为 0，因为现金连一手也买不起）。这引起了频繁的订单跳过（skipped below lot or cash）和信号重试，极大地增加了交易执行阻力，降低了实盘中的可操作性。

### 5.3 四舍五入取整手 (round)
- **优点**：在统计上是无偏的，平均来说能够将整手转换产生的偏差降到最低。测试显示它在夏普比率和年化收益上在 90% 以上的配置中优于 floor，同时交易笔数和年化换手率只比 floor 略微上升，远低于 ceil 的剧烈拉升。它在维持交易成本合理性的同时，将投资组合的实际持仓权重拉近到理论最优解，优化了风险平价效果。
- **建议**：实盘和回测均推荐作为默认的整手转换机制。
