# ETF Selection

This directory owns ETF screening and basket construction. It is intentionally separate from `platform/`; it only generates platform configs and optionally calls platform CLI commands.

## Workflow

1. Define ETF candidates by sleeve in `config/etf_universe.yaml`.
2. Run sleeve screening:

```powershell
.\env\python.exe etf_selection\scripts\screen_etf_sleeves.py --config etf_selection\config\etf_universe.yaml
```

3. Review reports under `etf_selection/reports/<timestamp>/`.
4. Generated platform configs are written under `etf_selection/generated_configs/<timestamp>/`.
5. Optional: run generated configs through the platform:

```powershell
.\env\python.exe etf_selection\scripts\screen_etf_sleeves.py --config etf_selection\config\etf_universe.yaml --run-experiments
```

## Design

- Sleeve screening is independent of platform internals.
- Backtests are delegated to `platform/scripts/run_platform_experiment.py`.
- Commodity ETFs are handled specially: broad commodity ETFs are preferred, but when no broad commodity ETF passes the 3-year history filter the selector can use multiple single-commodity ETFs.

## Outputs

- `sleeve_rankings.csv`
- `basket_scores.csv`
- `report.md`
- `summary.json`
- `correlations/<sleeve>.csv`
- `correlations/basket_<id>.csv`
- generated platform configs
