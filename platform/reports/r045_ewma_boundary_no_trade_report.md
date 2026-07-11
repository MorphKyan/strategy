# R045：风险平价 5/25 阈值触发后的无交易区边界回归执行

## 结论

`Failed`。候选在主训练样本明显降低 `annualized_turnover`，但低波 ETF 篮子在三种滑点情景的完整双月起点敏感性均出现实质 Sharpe 退化。未运行最终测试；候选源码、注册与配置已清理。

## 假设、数据与冻结

- 保持 `risk_parity_ewma` 的 EWMA 理论权重、月度检查与 5%/25% 触发条件；触发后沿当前权重至理论权重的线段，仅交易到最先回到无交易区的位置。有效带宽为 `min(0.05, 0.25 * target_weight)`；首次建仓仍全额到理论权重。
- 该边界交易形式有比例交易成本下多资产无交易区文献支持；本研究仅检验其在当前平台的执行层效果。[Leland (1999)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=206871)；[DeMiguel、Mei 与 Nogales (2014)](https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2379426_code644155.pdf?abstractid=2295345&mirid=1)。
- 三个篮子的共同最新交易日均为 `2026-07-10`，相对当前日 `2026-07-11` 为 1 天；共同历史最早为 `2019-01-18`、`2019-01-18`、`2017-08-24`，均超过三年。
- 候选于 2026-07-11 Asia/Shanghai 在主训练对照后冻结。所有研究 run 截至 `2025-06-30`，未使用 `2025-07-01` 及以后数据。

## 验证

```powershell
.\env\python.exe -m pytest platform\tests\test_platform_strategies.py -q
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\r045_domestic_ewma_boundary.yaml --baseline-config configs\baseline_r1_domestic_ewma.yaml --experiment-name r045_boundary_training_domestic_v2 --start-date 2019-01-18 --end-date 2025-06-30 --no-charts
.\env\python.exe platform\scripts\run_sensitivity.py --config <baseline-or-candidate-config> --calendar-month-step 2 --end-date 2025-06-30
```

`platform/tests/test_platform_strategies.py` 结果为 `12 passed`。主实验与敏感性均执行 `default`、`stress`、`dynamic_participation`。

## 主训练样本

从实际实验报告、`manifest.json`、`nav.csv`、`orders.csv` 和 `trades.csv` 读取。所有组合/情景的 `rejected_order_count` 均为 0。

| 配置 | 情景 | annualized_return | sharpe_ratio | max_drawdown | annualized_turnover | trade_count / order_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 国内四资产 | default | 14.37% | 2.0158 | -7.59% | 35.27% | 170 / 170 |
| 国内四资产 | stress | 14.27% | 2.0017 | -7.59% | 36.59% | 187 / 187 |
| 国内四资产 | dynamic_participation | 14.34% | 2.0109 | -7.59% | 35.49% | 177 / 177 |
| 低波三资产 | default | 15.55% | 2.3472 | -7.20% | 33.37% | 138 / 138 |
| 低波三资产 | stress | 15.42% | 2.3280 | -7.20% | 33.98% | 134 / 134 |
| 低波三资产 | dynamic_participation | 15.51% | 2.3414 | -7.20% | 33.08% | 131 / 131 |
| 等权三资产 | default | 12.15% | 1.8201 | -7.41% | 35.61% | 168 / 168 |
| 等权三资产 | stress | 12.05% | 1.8065 | -7.42% | 35.39% | 166 / 166 |
| 等权三资产 | dynamic_participation | 12.15% | 1.8203 | -7.41% | 35.64% | 167 / 167 |

候选把主样本年化金额换手由约 57%–62% 降至约 33%–36%，但交易笔数未下降。国内四资产 default 的基线→候选为 Sharpe `2.0309 -> 2.0158`、最大回撤 `-7.70% -> -7.59%`、年化金额换手 `60.93% -> 35.27%`、交易数 `164 -> 170`。

## 双月起点敏感性

每个篮子从最早共同交易日开始每 2 个自然月取起点，全部结束于 `2025-06-30`。数值是候选减基线的均值；Sharpe 达标表示 `delta >= -0.05`。

| 篮子 | 情景 | 起点数 | Sharpe delta | 达标比例 | annualized_return delta | max_drawdown delta | annualized_turnover delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 国内四资产 | default / stress / dynamic | 39 | -0.0435 / -0.0342 / -0.0432 | 69.2% / 76.9% / 64.1% | -0.79 / -0.72 / -0.79pp | +0.28 / +0.29 / +0.28pp | -21.96 / -22.03 / -22.00pp |
| 低波三资产 | default / stress / dynamic | 39 | -0.1251 / -0.1096 / -0.1228 | 10.3% / 10.3% / 10.3% | -0.90 / -0.79 / -0.88pp | -0.08 / -0.07 / -0.07pp | -25.43 / -25.69 / -25.37pp |
| 等权三资产 | default / stress / dynamic | 48 | -0.0599 / -0.0525 / -0.0606 | 52.1% / 60.4% / 50.0% | -0.77 / -0.71 / -0.77pp | +0.04 / +0.05 / +0.04pp | -21.27 / -21.34 / -21.31pp |

低波三资产的三种情景均硬失败，故不满足候选提交条件。未运行最终测试，也未在观察最终测试结果后调整任何候选内容。

## 产物与清理

- 主实验报告：`platform/reports/experiments/r045_boundary_training_*_v2_{default,stress,dynamic_participation}/`
- 敏感性报告：`platform/reports/sensitivity/risk_parity_ewma/{20260711_132707,20260711_132859,20260711_133109}/` 与 `platform/reports/sensitivity/risk_parity_ewma_boundary/{20260711_132803,20260711_133024,20260711_133215}/`
- 原始 artifacts：`platform/results/backtests/r045_boundary_training_*_v2_*/` 与 `platform/results/sensitivity_raw/`
- 已清理：`risk_parity_ewma_boundary` 源码、`BUILTIN_STRATEGIES` 注册、三份 R045 候选配置与对应单元测试；保留所有历史 artifacts 和报告。
