# R041 研究笔记：基于最小扭转有效押注数的风险预算拥挤度控制

## 基本信息

- 研究 ID：`R041`
- 课题：基于最小扭转有效押注数 (Minimum-Torsion ENB) 约束的风险预算拥挤度控制
- Owner：`codex-r041-20260625-094349`
- 创建时间：`2026-06-25 09:43:49 +08:00`
- 状态：`Failed`
- 标准实验报告：`platform/reports/r041_min_torsion_enb_failed_report.md`

## 冻结条件

- 训练样本截止：`2025-06-30`
- 最终测试起点：`2025-07-01`
- 冻结参数：`enb_min_ratio=0.55`、`max_bet_contribution=0.45`、`enb_blend=0.25`、`enb_max_iter=4`、`enb_penalty_strength=0.75`
- 冻结后未使用最终测试样本调参；最终测试未运行。

## 数据检查

- 所需本地行情最新日期均为 `2026-06-24`，满足 7 日新鲜度要求。
- `baseline_r7_cluster_representative_damped` 共同训练历史仅 `1.257` 年，剔除。
- 有效研究配置：`global_ewma`、`global_nasdaq_all_weather_ewma`、`us_blend_ewma`。

## 指标摘要

| 阶段 | 配置 | 策略 | annualized_return | sharpe_ratio | max_drawdown | annualized_turnover | trade_count | order_count | rejected_order_count |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 训练 | `r2_global_ewma` | baseline | `0.144993` | `1.296131` | `-0.114136` | `0.768019` | `335` | `336` | `1` |
| 训练 | `r2_global_ewma` | candidate | `0.149136` | `1.347178` | `-0.114806` | `0.868034` | `379` | `380` | `1` |
| 训练 | `r3_global_nasdaq_all_weather_ewma` | baseline | `0.144163` | `0.663707` | `-0.269733` | `0.793515` | `269` | `269` | `0` |
| 训练 | `r3_global_nasdaq_all_weather_ewma` | candidate | `0.145755` | `0.670602` | `-0.270125` | `0.759905` | `248` | `248` | `0` |
| 训练 | `us_blend_ewma` | baseline | `0.156574` | `0.836965` | `-0.261594` | `0.689476` | `234` | `234` | `0` |
| 训练 | `us_blend_ewma` | candidate | `0.163111` | `0.849735` | `-0.265301` | `0.739665` | `253` | `253` | `0` |

## 起点敏感性结论

- R2 有效起点：候选 Sharpe 均值 `1.851659` 低于基线 `1.856255`，换手率相对变化最大值 `18.13%` 超过 15% 门槛。
- R3 有效起点：候选 Sharpe 均值 `1.464481` 低于基线 `1.474648`，候选不低于基线的起点仅 `5/26`。
- US Blend 有效起点：候选 Sharpe 均值略高，但最大单一押注贡献均值从 `0.840426` 升至 `0.859724`，未达拥挤度控制目标。
- 三组候选的 `ENB/N` 最低均值分别为 `0.427042`、`0.316062`、`0.279489`，均低于冻结阈值 `0.55`。

## 结论

推荐：`Failed`。

理由：候选没有稳定提高有效押注数，也没有在主要多资产配置上保持训练起点 Sharpe 不退化。策略源码、注册和候选配置已物理清除；保留实验 artifacts 与中文报告供复核。
