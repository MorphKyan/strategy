# R054 虚拟 30Y 配置迁移真实 30Y ETF 全历史外部检验

## 结论

本研究完成冻结的 56 个源配置、两只真实 ETF、同窗虚拟参照及三滑点矩阵，共 `672` 个独立 run。真实 `511090` 与 `511130` 在全部 56 个配置、全部三滑点下，`sharpe_ratio` 均低于同窗虚拟 `511260_3X`；胜率为 `0/56`。因此现有虚拟 30Y 配置不能不经修改直接迁移到真实 30Y ETF并期待保持历史绩效，结论为 `Research-Only`，不输出正式平台配置，不建议直接实盘晋级。

这不等于真实 30Y 没有资金效率价值。真实替代的平均债券权重反而比虚拟参照高约 `0.51~0.83` 个百分点，说明现有风险平价参数并没有自动兑现“用更少名义本金获得相同风险贡献”的目标；需要显式的 DV01/久期风险预算与执行层映射，而不是只换 symbol。

R051/R052 已查看过重叠行情，所以本次是冻结参数的外部历史迁移检验，但不是纯净未见 OOS。真实 ETF 历史仍不足三年，证据不能支持长期有效性或常规规模实盘。

## 数据与同步修复

首次预检发现 `515080` 只到 `2026-06-24`。根因是开放式同步把 `start=None/end=None` 直接传给 Finshare，部分 provider 内部调用 `strftime` 失败；空结果又可能覆盖已有文件，随后新鲜度检查对 `NaT` 调用日期减法。此外，虚拟 `511260_3X` 被错误发送给外部 provider。

最小可复用修复：

- 开放日期规范化为 `1990-01-01` 至运行日；
- provider 返回空或无效行时显式失败并保留已有文件；
- 新鲜度检查先过滤无效日期，空日期给出明确错误；
- `_3X` 合成标的不调用外部 provider，保留规范生成器产物并继续校验新鲜度；
- 新增两个定向测试。

修复后 EastMoney 成功取得 `515080` 的 `1582` 行历史，最新日期为 `2026-07-10`。完整 inventory 的 16 个 required codes 均更新至 `2026-07-10`，无重复日期、无缺失 `adjust_factor`；真实 `511090/511130` 的 `volume/amount` 均为正。完整数据 hash 与审计见 `platform/results/r054_real30y_external_test/20260712_0130/manifest.json`。

## 冻结范围与窗口

- inventory：`platform/configs/` 中直接引用 `CN_ETF:511260_3X.SH` 的 56 个 YAML，其中经典首批 6 个，完整路径和 SHA-256 见 manifest。
- 仅替换资产定义、名称、code 和所有精确 universe 引用；算法、参数、调仓、费用和执行配置不变。
- `511090` 窗口：`2023-06-13` 至 `2026-07-10`，或受配置内其他标的上市日约束后的共同窗口。
- `511130` 窗口：`2024-03-28` 至 `2026-07-10`，或受其他标的约束后的共同窗口。
- 每个真实 ETF 均与原虚拟配置在完全相同窗口比较。
- 场景：`default`、`stress`、`dynamic_participation`。

## 主要结果

以下为 56 个配置的“真实减虚拟”平均差；指标从每个 run 的实际 `manifest.json.metrics`、`nav.csv`、`orders.csv`、`trades.csv`、`positions.csv` 计算，完整逐 run 表见 `r054_metrics.csv`，配对表见 `r054_pairs.csv`。

| ETF | scenario | annualized_return | annualized_volatility | sharpe_ratio | max_drawdown | annualized_turnover | trade_count | order_count | rejected_order_count | mean_cash_weight | mean_bond_weight |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 511090 | default | -2.45% | +0.10% | -0.3292 | -0.80% | +2.23% | +2.23 | +2.25 | +0.02 | -0.24% | +0.53% |
| 511090 | stress | -2.46% | +0.09% | -0.3306 | -0.81% | +2.26% | +2.48 | +2.48 | 0.00 | -0.21% | +0.51% |
| 511090 | dynamic_participation | -2.45% | +0.10% | -0.3296 | -0.80% | +2.19% | +2.16 | +2.18 | +0.02 | -0.24% | +0.54% |
| 511130 | default | -3.18% | -0.15% | -0.3369 | -0.41% | -0.57% | -0.09 | -0.05 | +0.04 | -0.26% | +0.83% |
| 511130 | stress | -3.14% | -0.15% | -0.3342 | -0.42% | -0.78% | -0.39 | -0.38 | +0.02 | -0.28% | +0.83% |
| 511130 | dynamic_participation | -3.18% | -0.15% | -0.3369 | -0.41% | -0.54% | -0.02 | +0.02 | +0.04 | -0.26% | +0.83% |

六经典首批的退化更明显：`511090` 三滑点平均 `sharpe_ratio` 差为 `-0.4036~-0.4109`，`annualized_return` 差为 `-3.23%~-3.27%`；`511130` 分别为 `-0.4143~-0.4167` 与 `-4.16%~-4.24%`。三滑点没有改变方向或排序结论。

执行层总体没有出现大规模拒单：平均 `rejected_order_count` 差接近 0，但 `511090` 平均换手和交易数略增。虚拟标的的 `volume/amount` 只用于机制参照，未用于真实容量结论。

## 精确命令

```powershell
.\env\python.exe -m pytest platform\tests\test_platform_core.py -q -k "market_sync_"
.\env\python.exe platform\scripts\sync_platform_data.py --config configs\baseline_r1_user_holdings.yaml --fetch
.\env\python.exe r054_runner_tmp.py prep
.\env\python.exe r054_runner_tmp.py classic
.\env\python.exe r054_runner_tmp.py all
.\env\python.exe r054_aggregate_tmp.py
```

临时脚本 `r054_runner_tmp.py` 与 `r054_aggregate_tmp.py` 已删除。

## Artifacts

- 配置/数据 manifest：`platform/results/r054_real30y_external_test/20260712_0130/manifest.json`
- 六经典 raw artifacts：`platform/results/r054_real30y_external_test/20260712_0130/classic/`
- 完整 672 run raw artifacts：`platform/results/r054_real30y_external_test/20260712_0130/all/`
- 逐 run 指标：`platform/results/r054_real30y_external_test/20260712_0130/r054_metrics.csv`
- 真实/虚拟配对指标：`platform/results/r054_real30y_external_test/20260712_0130/r054_pairs.csv`
- 汇总：`platform/results/r054_real30y_external_test/20260712_0130/r054_summary.json`
- 研究派生配置：`platform/configs/research_artifacts/20260712_0130/`

## 建议

1. 不直接把现有虚拟 30Y 配置的 symbol 替换为真实 ETF 后上线。
2. 下一步研究应把风险模型资产与执行标的解耦，并预先冻结 DV01/久期换算、最大名义权重及现金释放规则。
3. 在真实历史严格超过三年、影子成交数据充分前，只允许 `Research-Only` 或小规模影子观察。
