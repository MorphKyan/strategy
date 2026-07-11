# R046：中国真实 ETF 多资产双速趋势防御策略——失败报告

## 结论

`Failed`。候选在训练样本主对照的三种滑点情景均未达到冻结门槛，故不运行自然月起点敏感性或 `2025-07-01` 之后最终测试；候选源码、注册、配置和测试已清理。本报告与已生成的原始 artifacts 保留。

## 假设、范围与冻结规则

候选 `china_dual_speed_trend_defensive` 对 `510300`、`511260`、`518880`、`512890` 分别使用自身的 63/252 日后复权绝对趋势；两项均严格为正时目标为 25%，恰一项为正时为 12.5%，否则为 0%，未使用预算留为现金。它不调用风险平价、协方差、收益预测、横截面排名或 ETF 扩充。

假设依据为多资产时间序列动量的跨市场证据与快慢动量状态划分研究：[Moskowitz, Ooi and Pedersen (2012)](https://www.sciencedirect.com/science/article/pii/S0304405X11002613)、[Han, Zhou and Zhu (2023)](https://www.sciencedirect.com/science/article/pii/S0304405X23001034)。同时预注册其可能在资产逐一趋势中表现为滞后、高现金与频繁切换的反证风险：[Huang, Li and Wang (2020)](https://www.sciencedirect.com/science/article/abs/pii/S0304405X19301953)。

训练样本固定为 `2019-01-18` 至 `2025-06-30`；最终测试起点固定为 `2025-07-01`，但从未读取或运行。主基线是 `r8_permanent_real_fixed_weight_threshold.yaml`，机制基线是 `r8_permanent_real_equal_weight_monthly.yaml`。预冻结主门槛要求三情景中 Sharpe 差不低于 `-0.05`、最大回撤绝对值至少收窄 10%、年化收益下降不超过 1.5 个百分点、换手增幅不超过 30%。

## 数据与时序审计

- 四份原始行情均截至 `2026-07-10`，无重复日期；共同区间为 `2019-01-18` 至 `2026-07-10`、1810 个交易日，训练共同历史超过三年。
- 执行了 `sync_platform_data.py` 本地校验。复权 sidecar 在训练段内完整；平台按 `data.py` 的既有规则将各资产复权因子对原始行情日期前向填充。
- 候选在月末检查时先调用 `get_price_frame(..., context.date)`，再显式过滤 `index < context.date`。因此 `r63 = P[t-1]/P[t-64]-1` 与 `r252 = P[t-1]/P[t-253]-1` 不使用执行日收盘；不足 253 个共同观察时保持 0% 目标。
- 候选实现 SHA256：`8AC948BE859C490C0958D513D574CBE862C1CC9E...`；候选配置 SHA256：`39CB719FBF1268E1E545B5A5778CD54CA61BCE3C...`；研究时 `HEAD`：`142ba2d4d71aabdb8996d3e70debfaf6dd709d4d`。

## 精确命令

```powershell
.\env\python.exe platform\scripts\sync_platform_data.py --config configs\r8_permanent_real_fixed_weight_threshold.yaml
.\env\python.exe platform\scripts\get_common_date_range.py --codes 510300 511260 518880 512890
.\env\python.exe -m pytest platform\tests\test_china_dual_speed_trend.py -q
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\r046_china_dual_speed_trend_defensive.yaml --baseline-config configs\r8_permanent_real_fixed_weight_threshold.yaml --experiment-name r046_training_vs_threshold --start-date 2019-01-18 --end-date 2025-06-30 --slippage-scenario all --no-charts
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\r046_china_dual_speed_trend_defensive.yaml --baseline-config configs\r8_permanent_real_equal_weight_monthly.yaml --experiment-name r046_training_vs_monthly_equal_weight --start-date 2019-01-18 --end-date 2025-06-30 --slippage-scenario all --no-charts
```

## 实际训练指标

| 情景 | 对照 | annualized_return | sharpe_ratio | max_drawdown | annualized_turnover | trade_count / order_count / rejected_order_count |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| default | 候选 | 4.88% | 0.7239 | -9.27% | 81.38% | 203 / 203 / 0 |
| default | 主基线 | 10.91% | 1.1715 | -9.52% | 10.24% | 24 / 24 / 0 |
| stress | 候选 | 4.69% | 0.6948 | -9.28% | 80.49% | 194 / 194 / 0 |
| stress | 主基线 | 10.88% | 1.1682 | -9.53% | 10.25% | 24 / 24 / 0 |
| dynamic_participation | 候选 | 4.76% | 0.7071 | -9.27% | 80.71% | 195 / 195 / 0 |
| dynamic_participation | 主基线 | 10.89% | 1.1643 | -9.52% | 9.97% | 24 / 24 / 0 |

相对主基线，候选 Sharpe 差为 `-0.4475`、`-0.4735`、`-0.4572`，年化收益差为 `-6.03`、`-6.20`、`-6.13` 个百分点；回撤仅收窄约 `0.24~0.25` 个百分点，远低于 10% 相对收窄门槛；年化换手则增加约 `68~71` 个百分点。相对月度等权机制基线，三情景 Sharpe 差为 `-0.4767`、`-0.5007`、`-0.4931`，年化收益差为 `-6.14`、`-6.29`、`-6.26` 个百分点，也均失败。

候选的 `fee_total` 为 `2731.40`、`2676.71`、`2684.16`，主基线为 `378.38`、`378.30`、`372.58`；三情景均无拒单。候选 `max_pending_intent_count` 为 4，未见由拒单或持续待执行意图导致的失败。候选 `average_cash_weight` 为约 38.4%，主基线不足 0.5%，说明长期现金拖累是核心归因之一。

## 机制审计

65 个可计算月末决策中，`510300/511260/518880/512890` 的 `0/0.5/1` 状态次数分别为 `22/24/19`、`0/16/49`、`6/14/45`、`5/13/47`；状态切换次数为 `19/12/9/20`。目标现金权重中位数为 25%、95% 分位为 50%、最大为 62.5%；实际日度现金权重中位数为 25.14%、95% 分位和最大值均为 100%。没有完整全现金目标月，但候选仍因离散状态反复切换产生远高于两种基线的成交额与费用。

## 失败判定与后续动作

主训练三情景同时违反 Sharpe、年化收益和换手硬门槛，且机制基线同样明显优于候选。按预注册规则立即停止，未进行起点敏感性和最终测试，未根据结果修改 63/252 窗口、档位、预算、资产池、现金处理或检查频率。后续若研究中国 ETF 的趋势防御，必须作为新课题重新提出可证伪假设与固定规则，不能复用本候选做事后调参。

原始结果位于 `platform/results/backtests/r046_training_vs_threshold_*` 与 `platform/results/backtests/r046_training_vs_monthly_equal_weight_*`；标准化指标位于相应的 `platform/reports/experiments/` 目录。
