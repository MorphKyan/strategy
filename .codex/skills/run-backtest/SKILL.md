---
name: run-backtest
description: Run this repository's backtest workflow and normalize the resulting metrics. Use when Codex needs to find the right command, execute baseline or variant runs, inspect artifacts under results, and produce a stable report under reports/experiments without inventing missing metrics.
---

# Run Backtest

Use this workflow:
1. Prefer `.\env\python.exe scripts/run_experiment.py --strategy <name> --config <config>` for stable outputs.
2. If needed, run the baseline and the target variant separately.
3. Verify that raw artifacts were created under `results/<strategy>/<timestamp>/`.
4. Read the standardized metrics written under `reports/experiments/<strategy>/<timestamp>/metrics.json`.
5. If a command fails, report the exact failure and the likely next fix.

The clean summary should include:
- total return
- annualized return
- annualized volatility
- max drawdown
- sharpe ratio
- turnover
- trade count
- whether out-of-sample metrics were available
