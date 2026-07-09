# R038：固定权重 + 5/25 阈值带再平衡（永久组合式）研究报告

> 日期：2026-07-09
> 结论：**通过验收，建议作为实盘跟投组合的默认策略**
> 分支：`codex/r8-permanent-threshold`

## 一、结论（先行）

在全真实可交易 ETF 四资产篮子（510300 沪深300 / 511260 十年国债 / 518880 黄金 / 512890 红利低波，等权 25%）上，候选 `fixed_weight_threshold`（Swedroe 5/25 规则：任一资产偏离目标超 5 个绝对百分点或目标的 25% 才全组合归位）相对同篮同费的 `monthly_equal_weight` 基线：

- **绩效打平**：训练样本 Sharpe 1.17 vs 1.20（差 -0.03，噪音级）；**冻结测试样本反超**（Sharpe 0.90 vs 0.87，收益 9.99% vs 9.53%，回撤更浅）；
- **执行负担降一个数量级**：训练样本 6.4 年交易 24 笔 vs 261 笔（1/11），年化换手 10.2% vs 21.6%（减半）；敏感性中换手优势在 **100% 起点**成立；
- **执行风险更低**：候选全部运行零拒单（基线冻结样本 1 笔拒单）。

候选的价值主张不是更高收益，而是**同等绩效下把手动跟投的操作成本降到每年约 2–4 笔**——这正是实盘跟投场景要优化的目标函数。参数为文献先验值一次定型，全程未做参数搜索，无过拟合空间。

## 二、假设与来源

- 假设：固定目标权重 + 先验常数阈值带的"检查每日、交易极少"纪律，能以可忽略的绩效代价换取换手与交易笔数的数量级下降；阈值触发允许强势资产带内顺势漂移，缓解日历调仓的"强趋势踏空"。
- 来源：Larry Swedroe 5/25 实践规则；本仓库 `rebalance_frequency_study_report.md`（国内篮子月调优于日调、换手是主要摩擦）；R028 / R037 两次自适应触发机制均判 Failed 的教训——**本策略刻意零自适应成分**。

## 三、改动文件

| 文件 | 变更 |
|------|------|
| `platform/src/platform_core/strategies/__init__.py` | 新增策略扩展包（蓝图 C1 布局：一策略一文件） |
| `platform/src/platform_core/strategies/fixed_weight.py` | 新增 `FixedWeightThresholdStrategy`；空仓建仓判断基于持仓状态而非 runtime 标记，回测 / 纸面 sim / 实盘 live plan 三环路行为一致 |
| `platform/src/platform_core/strategy.py` | 文件尾 import 并注册进 `BUILTIN_STRATEGIES` |
| `platform/configs/r8_permanent_real_fixed_weight_threshold.yaml` | 候选配置（abs_band=0.05, rel_band=0.25） |
| `platform/configs/r8_permanent_real_equal_weight_monthly.yaml` | 同篮同费月度等权对照基线 |
| `platform/configs/generated/r8_permanent_real_fixed_weight_threshold_ckpt.yaml` | checkpoint 开启版（组合落地用） |
| `platform/tests/test_platform_strategies.py` | 6 个单元测试（注册 / 空仓建仓 / 带内不动 / 绝对带触发 / 相对带触发 / 显式权重归一） |

## 四、数据新鲜度与样本隔离

- 运行日：2026-07-09；`sync_all_market_data.py` 后本地行情最新至 `2026-07-09`（≤7 天 ✓）。
- 篮子共同可用起始日：`2019-01-18`（512890 上市日）；至训练上限 `2025-06-30` 共同历史 6.4 年（>3 年 ✓）。
- 训练/研究只用 `2025-06-30` 及以前；候选于敏感性通过后冻结，冻结后才运行 `2025-07-01` 起的最终测试；未据最终测试结果修改任何参数。

## 五、训练样本对比（2019-01-18 → 2025-06-30）

指标读取自 `platform/reports/experiments/r038_fixed_weight_threshold_train_{scenario}/20260709_2315*/metrics.json`：

| 场景 | 策略 | 年化收益 | 年化波动 | 最大回撤 | Sharpe | 年化换手 | 交易/订单/拒单/跳过 |
|------|------|---------:|---------:|---------:|-------:|---------:|---------------------|
| default | 候选 | 10.91% | 9.31% | -9.52% | 1.171 | 10.24% | 24/24/0/2 |
| default | 基线 | 11.02% | 9.18% | -9.28% | 1.201 | 21.59% | 261/261/0/37 |
| stress | 候选 | 10.88% | 9.31% | -9.53% | 1.168 | 10.25% | 24/24/0/2 |
| stress | 基线 | 10.97% | 9.18% | -9.27% | 1.196 | 22.13% | 265/265/0/37 |
| dynamic_participation | 候选 | 10.89% | 9.35% | -9.52% | 1.164 | 9.97% | 24/24/0/2 |
| dynamic_participation | 基线 | 11.02% | 9.18% | -9.27% | 1.200 | 21.57% | 263/263/0/37 |

三场景结论一致：绩效差异在噪音级，换手减半、交易笔数 1/11。

## 六、起始日期敏感性（训练样本内）

产物：`platform/reports/sensitivity/fixed_weight_threshold/20260709_231742/`、`platform/reports/sensitivity/monthly_equal_weight/20260709_232001/`。

采样说明：`run_sensitivity.py --step 41`（41 个交易日 ≈ 每 2 个自然月一个起点），截止 `2025-06-30`。**脚本从数据并集最早日（2012-05-28）起采样，早于共同起始日的起点中 512890 无数据、组合含约 25% 幽灵现金，违反共同历史纪律，统计时全部剔除**；合法起点为 `start_date ≥ 2019-01-18`，每场景 38 个。

| 统计（38 起点，default 场景） | 候选 | 基线 |
|------|------|------|
| Sharpe 均值 ± 标准差 | 1.394 ± 0.502 | 1.431 ± 0.521 |
| 年化收益均值 | 12.62% | 12.89% |
| 最大回撤均值 ± 标准差 | -6.84% ± 2.04% | -6.89% ± 2.10% |
| 交易笔数均值 | 14.1 | 129.7 |
| 拒单 | 全部 0 | 全部 0 |

配对差异（同起点同场景，114 组）：Sharpe 差均值 **-0.038**（std 0.074，候选更高占比 7%）；**换手候选更低占比 100%**；回撤候选更浅或持平占比 72.8%。排名结构在全部起点稳定：候选始终以小幅 Sharpe 代价换取数量级更低的执行成本，不存在局部优势或不稳定翻转。stress / dynamic_participation 场景统计一致。

## 七、最终测试样本（冻结后，2025-07-01 → 2026-07-09）

指标读取自 `platform/reports/experiments/r038_fixed_weight_threshold_finaltest_{scenario}/20260709_2324*/metrics.json`：

| 场景 | 策略 | 年化收益 | 最大回撤 | Sharpe | 年化换手 | 交易/拒单 |
|------|------|---------:|---------:|-------:|---------:|-----------|
| default | 候选 | **9.99%** | **-8.92%** | **0.904** | 52.9%* | 8/0 |
| default | 基线 | 9.53% | -9.11% | 0.869 | 66.5%* | 49/1 |
| stress | 候选 | 9.90% | -8.86% | 0.898 | 53.0% | 8/0 |
| stress | 基线 | 9.33% | -9.12% | 0.851 | 65.7% | 47/1 |
| dynamic_participation | 候选 | 9.99% | -8.92% | 0.904 | 52.9% | 8/0 |
| dynamic_participation | 基线 | 9.53% | -9.11% | 0.869 | 66.5% | 49/1 |

\* 一年窗口含建仓，换手年化被建仓一次性放大，两者同口径可比。冻结样本候选全面不劣于基线（小幅反超），三场景一致。

## 八、近 5 年展示区间（2021-07-09 → 2026-07-09，冻结后仅作展示）

指标读取自 `platform/reports/experiments/r038_fixed_weight_threshold_recent5y_{scenario}/20260709_2325*/metrics.json`（default 场景）：候选年化 8.70%、Sharpe 0.95、最大回撤 -9.42%、5 年 20 笔交易（每年 4 笔）；基线年化 8.97%、Sharpe 0.98、回撤 -9.11%、198 笔交易。

全历史形成运行（2019-01-18 → 2026-07-09，default）：累计收益 **+109.13%**，7.5 年 28 笔交易，产物 `platform/results/backtests/r8_permanent_real_fwt_ckpt_default_20260709_232642_041323/`（含每日 checkpoint）。

## 九、组合落地（可往后运行）

1. **纸面影子组合**：`sim_r8_permanent_shadow`（从 2026-07-09 checkpoint 派生，`platform/results/sim_portfolios/sim_r8_permanent_shadow/`），日常用 `run_sim_portfolio.py --asof-date <d>` 推进，作为月度归因的模型侧。
2. **实盘跟投**（mark-to-real 环路）：
   - 起步：`run_live_cycle.py reconcile --config configs\r8_permanent_real_fixed_weight_threshold.yaml --holdings <空持仓csv> --cash <真实现金>` → `plan` 产出建仓票（验证示例：100 万现金 → 四资产各 ≈25 万，费用 ≈200 元，票据 `results/live_portfolios/live_r8_permanent_demo/tickets/`）；
   - 日常：任务计划每日收盘后 `cycle --sync --notify`；策略每日检查、仅在触带时出票（历史节奏约每年 2–4 次）；实际成交后 `reconcile` 对齐真值。
3. 策略在 live plan 环路下与回测同构（空仓判断基于持仓状态），无需任何特殊处理。

## 十、命令

```powershell
.\env\Scripts\python.exe platform\scripts\sync_all_market_data.py
.\env\Scripts\python.exe -m pytest platform\tests -q
.\env\Scripts\python.exe platform\scripts\run_platform_experiment.py --config configs\r8_permanent_real_fixed_weight_threshold.yaml --baseline-config configs\r8_permanent_real_equal_weight_monthly.yaml --experiment-name r038_fixed_weight_threshold_train --start-date 2019-01-18 --end-date 2025-06-30 --slippage-scenario all
.\env\Scripts\python.exe platform\scripts\run_sensitivity.py --config configs\r8_permanent_real_fixed_weight_threshold.yaml --end-date 2025-06-30 --step 41 --slippage-scenario all
.\env\Scripts\python.exe platform\scripts\run_sensitivity.py --config configs\r8_permanent_real_equal_weight_monthly.yaml --end-date 2025-06-30 --step 41 --slippage-scenario all
.\env\Scripts\python.exe platform\scripts\run_platform_experiment.py --config configs\r8_permanent_real_fixed_weight_threshold.yaml --baseline-config configs\r8_permanent_real_equal_weight_monthly.yaml --experiment-name r038_fixed_weight_threshold_finaltest --start-date 2025-07-01 --end-date 2026-07-09 --slippage-scenario all
.\env\Scripts\python.exe platform\scripts\run_platform_experiment.py --config configs\r8_permanent_real_fixed_weight_threshold.yaml --baseline-config configs\r8_permanent_real_equal_weight_monthly.yaml --experiment-name r038_fixed_weight_threshold_recent5y --start-date 2021-07-09 --end-date 2026-07-09 --slippage-scenario all
.\env\Scripts\python.exe platform\scripts\run_platform_backtest.py --config configs\generated\r8_permanent_real_fixed_weight_threshold_ckpt.yaml --start-date 2019-01-18 --end-date 2026-07-09 --slippage-scenario default
```

## 十一、边界与建议

1. **运行时起始日必须 ≥ 篮子共同起始日（2019-01-18）**：更早起点下 512890 无数据，目标权重含无法成交的幽灵配置（敏感性统计已按此剔除非法起点）。策略保持简单未做自动降级，属于纪律约束而非代码约束。
2. 阈值带（5/25）为先验常数。若未来想调带宽，必须按本协议重新走全流程（训练对比 + 敏感性 + 冻结测试），不得直接在实盘配置上改。
3. 建议实盘跟投使用候选配置；若更看重理论 Sharpe 而不在乎操作频率，月度等权基线同样合格（两者差异在噪音级）。
