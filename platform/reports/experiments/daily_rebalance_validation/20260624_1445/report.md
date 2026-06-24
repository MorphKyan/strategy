# 按日调仓修复与验证报告

## 结论

本次修复后，`rebalance_frequency: daily` 已在 `RiskParityStrategy._is_rebalance_day()` 中真正按每个交易日返回调仓检查日。用 `baseline_r6_adaptive_risk_deviation.yaml` 的实际交易日历验证，daily 检查日为 2132/2132 个交易日；同一日历下 quarterly 只有 36 个检查日。

需要注意：daily 表示每日检查是否需要生成目标仓位，不表示每天必然成交。实际是否下单仍取决于策略触发条件、`rebalance_threshold`、危机触发、交易限制、lot size、待执行意图等执行规则。

## 修改文件

- `platform/src/platform_core/strategy.py`
  - 在 `_is_rebalance_day()` 中新增 `freq == "daily"` 分支，返回 `True`。
- `platform/tests/test_platform_core.py`
  - 新增单元测试，验证普通非月末、非季末交易日下 daily 返回 `True`，quarterly 返回 `False`。

## 验证命令

```powershell
.\env\python.exe -m pytest platform\tests\test_platform_core.py
```

结果：`18 passed`。

数据新鲜度检查：

- `baseline_r6_adaptive_risk_deviation.yaml` 所需数据最新共同日期为 `2026-06-23`，距当前日期 `2026-06-24` 为 1 天，满足规则。
- `baseline_r7_cluster_representative_damped.yaml` 初始检查时，`510310` 和 `511130` 最新日期为 `2026-06-10`，距 `2026-06-24` 为 14 天，不满足规则。直接校验命令未带 `--fetch`，失败信息为陈旧数据：

```powershell
.\env\python.exe platform\scripts\sync_platform_data.py --config configs\baseline_r7_cluster_representative_damped.yaml
```

随后直接调用平台同步 API，将 `baseline_r7` 全部配置标的同步到 `2026-06-24`。复查结果：`518880`、`510310`、`159985`、`159981`、`511130`、`513500` 最新日期均为 `2026-06-24`，满足规则。

## 是否真正按日检查

基于 `baseline_r6_adaptive_risk_deviation.yaml` 的交易日历：

| 频率 | 检查日数量 | 交易日数量 | 首批检查日 |
|---|---:|---:|---|
| daily | 2132 | 2132 | 2017-08-24, 2017-08-25, 2017-08-28, 2017-08-29 |
| monthly | 107 | 2132 | 2017-08-31, 2017-09-29, 2017-10-31, 2017-11-30 |
| quarterly | 36 | 2132 | 2017-09-29, 2017-12-29, 2018-03-30, 2018-06-29 |

这证明 daily 不再落入 quarterly 默认分支。

## 回测对比

对比口径：同一份配置，仅改变 `strategies.segments[0].params.rebalance_frequency`。

### baseline_r6_adaptive_risk_deviation.yaml

- daily：`baseline_r6_adaptive_daily_validation_20260624_144549_359673`
- quarterly：`baseline_r6_adaptive_quarterly_validation_20260624_144605_017928`

原始结果路径：

- daily：`platform/results/backtests/daily_rebalance_validation/baseline_r6_adaptive_daily_validation_20260624_144549_359673`
- quarterly：`platform/results/backtests/daily_rebalance_validation/baseline_r6_adaptive_quarterly_validation_20260624_144605_017928`
- 对比摘要：`platform/results/backtests/daily_rebalance_validation/summary_r6_daily_vs_quarterly.json`

| 指标 | daily | quarterly | daily - quarterly |
|---|---:|---:|---:|
| total_return | 165.64% | 156.90% | +8.74pct |
| max_drawdown | -7.55% | -7.47% | -0.09pct |
| trade_count | 159 | 74 | +85 |
| order_count | 576 | 253 | +323 |
| signal_order_dates_count | 476 | 209 | +267 |
| filled_order_dates_count | 59 | 30 | +29 |
| turnover_total | 4,502,244.59 | 3,510,207.25 | +992,037.34 |
| annualized_turnover | 34.40% | 26.98% | +7.42pct |
| turnover_amount_ratio | 291.06% | 228.28% | +62.79pct |
| pending_intent_count | 0 | 3 | -3 |

### baseline_r7_cluster_representative_damped.yaml

- daily：`baseline_r7_cluster_daily_validation_20260624_144831_225679`
- quarterly：`baseline_r7_cluster_quarterly_validation_20260624_144833_584559`

原始结果路径：

- daily：`platform/results/backtests/daily_rebalance_validation/baseline_r7_cluster_daily_validation_20260624_144831_225679`
- quarterly：`platform/results/backtests/daily_rebalance_validation/baseline_r7_cluster_quarterly_validation_20260624_144833_584559`
- 对比摘要：`platform/results/backtests/daily_rebalance_validation/summary_r7_daily_vs_quarterly.json`

| 指标 | daily | quarterly | daily - quarterly |
|---|---:|---:|---:|
| total_return | 45.36% | 53.20% | -7.84pct |
| max_drawdown | -4.34% | -4.87% | +0.53pct |
| trade_count | 74 | 36 | +38 |
| order_count | 142 | 113 | +29 |
| signal_order_dates_count | 81 | 85 | -4 |
| filled_order_dates_count | 16 | 8 | +8 |
| turnover_total | 1,697,847.54 | 1,502,364.54 | +195,483.00 |
| annualized_turnover | 62.81% | 53.21% | +9.60pct |
| turnover_amount_ratio | 132.59% | 112.33% | +20.26pct |
| pending_intent_count | 1 | 0 | +1 |

## 效果分析

按日检查后，策略能在非季末及时响应权重偏离和波动触发。`baseline_r6` 中，目标信号日期从 209 增至 476，实际成交日期从 30 增至 59，成交笔数从 74 增至 159。收益端，daily 的总收益率比 quarterly 高 8.74 个百分点。

代价是交易频率和换手明显上升：`baseline_r6` 的 `annualized_turnover` 增加 7.42 个百分点，`turnover_amount_ratio` 增加 62.79 个百分点，订单数增加 323。最大回撤基本持平但略差 0.09 个百分点。

`baseline_r7` 的表现不同：daily 的成交日期从 8 增至 16，成交笔数从 36 增至 74，换手上升；最大回撤改善 0.53 个百分点，但总收益低于 quarterly 7.84 个百分点。这说明 daily 调仓频率并非稳定提升收益，具体效果取决于策略触发逻辑和资产池。

综合判断：daily 修复后确实生效；对 `baseline_r6`，每日检查提高了响应速度和总收益，但以更高换手与交易次数为代价；对 `baseline_r7`，每日检查降低回撤但牺牲收益并增加换手。该结果是修复验证和观察性对比，不构成可投策略提交结论；完整研究提交仍需按仓库规则执行训练/测试切分、起点敏感性和最终测试验证。
