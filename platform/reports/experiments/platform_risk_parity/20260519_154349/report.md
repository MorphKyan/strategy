# Platform Risk Parity Run

## 假设

The existing inverse-volatility risk parity logic can be represented as a new platform target-weight strategy while letting the platform execution layer handle fees, lots, price limits, suspended assets, pending intents, checkpoints, and run artifacts.

## Files Changed

- `data/510300.csv`
- `data/518880.csv`
- `data/511260.csv`
- `src/platform_core/strategy.py`
- `configs/platform_risk_parity.yaml`
- `tests/test_platform_core.py`

## 命令

```powershell
.\env\python.exe -m pytest tests\test_platform_core.py
.\env\python.exe scripts\run_platform_backtest.py --config configs\platform_risk_parity.yaml
```

## Data

- Updated `510300`, `518880`, and `511260` local CSV files through `2026-05-19`.
- Each ETF added 42 rows from `2026-03-17` through `2026-05-19`.
- Platform run used the common-history period from `2017-08-24` through `2026-05-19`.

## 产物

- 平台原始结果路径： `results/platform/platform_risk_parity_20260519_154349/`
- 标准化报告路径： `reports/experiments/platform_risk_parity/20260519_154349/report.md`

## 指标

| Metric | Value |
| --- | ---: |
| Start date | 2017-08-24 |
| End date | 2026-05-19 |
| Observations | 2116 |
| Total return | 59.00% |
| Max drawdown | -5.04% |
| Trade count | 50 |
| Turnover total | 3452362.90 |
| Pending intents at end | 1 |

## Legacy Tool Check

Legacy command:

```powershell
.\env\python.exe scripts\run_experiment.py --strategy risk_parity --config configs\risk_parity.yaml --skip-baseline
```

Legacy raw result path: `results/risk_parity/20260519_155156/`

Legacy standardized report path: `reports/experiments/risk_parity/20260519_155155/`

| Metric | Platform | Legacy | Delta |
| --- | ---: | ---: | ---: |
| Observations | 2116 | 2115 | +1 |
| Total return | 58.9951% | 62.3930% | -3.3979 pp |
| Annualized return | 5.6804% | 5.9499% | -0.2695 pp |
| Annualized volatility | 3.7451% | 3.5309% | +0.2143 pp |
| Max drawdown | -5.0395% | -4.4066% | -0.6329 pp |
| Sharpe ratio | 1.5167 | 1.6851 | -0.1684 |
| Trade count | 50 | 48 | +2 |
| Turnover total ratio | 3.4524 | 3.9090 | -0.4566 |

The results are not identical. The platform has one extra observation (`2018-08-17`) because it uses a union trading calendar with suspended carry-forward bars, while the legacy research path effectively uses common aligned price dates. The platform also applies cash, round-lot execution, minimum fees, rejected orders, and pending-intent retries; the legacy strategy simulates fractional portfolio-value trades inside the strategy.

本次运行的仓库输出中没有样本外指标。

## 说明

The final pending intent is `CN_ETF:511260.SH`, created on `2026-03-31` and retried through `2026-05-19`. It remains pending because the account cash is insufficient to buy another full lot.

## 建议

Refine. The strategy runs end-to-end on the new platform and produces complete artifacts, but the adapter should be reviewed against the legacy research implementation before treating platform results as directly comparable.
