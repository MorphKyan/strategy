# Strategy Workspace

This repository now keeps the two backtest systems in separate top-level directories.

## Directory Map

- `research/`: the original risk-parity research backtest system.
- `platform/`: the newer daily event-driven retail backtest and simulated-portfolio platform.
- `backup/`: archived pre-refactor scripts.
- `env/`: local Python environment shared by the workspace.

Each system owns its own source, configs, data, scripts, docs, reports, and results. Run commands from the repository root by pointing at the target system's entry script, or run them from inside that system directory.

## Research System

See `research/README.md`.

Common commands:

```powershell
.\env\python.exe research\main.py --config configs\risk_parity.yaml --strategy risk_parity
.\env\python.exe research\scripts\run_experiment.py --strategy risk_parity --config configs\risk_parity.yaml
.\env\python.exe research\scripts\select_risk_parity_universe.py --write-configs
```

Relative paths in research commands are resolved from `research/`.

## Platform System

See `platform/README.md`.

Common commands:

```powershell
.\env\python.exe platform\scripts\run_platform_backtest.py --config configs\platform_mvp.yaml
.\env\python.exe platform\scripts\run_platform_experiment.py --config configs\platform_risk_parity.yaml
.\env\python.exe platform\scripts\run_sensitivity.py --config configs\platform_risk_parity.yaml
.\env\python.exe platform\scripts\validate_hfq_data.py --codes 510300 518880 511260
.\env\python.exe platform\scripts\sync_platform_data.py --config configs\platform_m3m4.yaml
.\env\python.exe platform\scripts\run_sim_portfolio.py --config configs\platform_m3m4.yaml --checkpoint <checkpoint.json> --asof-date 2026-05-30
```

Relative paths in platform commands are resolved from `platform/`.
