# Risk-Parity Research Backtest System

This directory contains the original research workflow for controlled, additive experiments around the risk-parity baseline.

## Directory Map

- `main.py`: research backtest entrypoint.
- `src/`: research source code.
  - `src/data_handler.py`: local ETF data loading and Finshare backfill.
  - `src/engine.py`: vector-style portfolio rebalance engine.
  - `src/strategies/`: dynamically loaded strategy modules.
  - `src/strategies/risk_parity.py`: baseline strategy.
  - `src/analysis/`: plotting and sensitivity analysis helpers.
- `configs/`: research YAML configs.
  - `configs/risk_parity.yaml`: fixed baseline config.
  - `configs/risk_parity_etf_universe.yaml`: ETF universe for basket screening.
  - `configs/generated/`: additive generated basket configs.
- `data/`: research market data and adjustment-factor files.
- `scripts/`: research experiment and ETF screening scripts.
- `reports/`: standardized experiment and literature notes.
- `results/`: raw research backtest artifacts.

## Commands

Run from the repository root:

```powershell
.\env\python.exe research\main.py --config configs\risk_parity.yaml --strategy risk_parity
.\env\python.exe research\scripts\run_experiment.py --strategy risk_parity --config configs\risk_parity.yaml
.\env\python.exe research\scripts\select_risk_parity_universe.py --write-configs
```

The research entrypoints resolve relative paths from `research/`, so `configs/risk_parity.yaml` means `research/configs/risk_parity.yaml`.

## Outputs

- Raw backtests: `research/results/<strategy>/<timestamp>/`
- Standard reports: `research/reports/experiments/<strategy>/<timestamp>/`
- Literature notes: `research/reports/literature/`

## Boundary

This system should remain focused on small, auditable research experiments. Add risk-parity variants under `research/src/strategies/`; do not modify `research/src/strategies/risk_parity.py` unless the baseline is explicitly being changed.
