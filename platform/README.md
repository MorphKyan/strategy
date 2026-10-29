# Retail Backtest Platform

This directory contains the newer daily event-driven platform runtime. It is separate from the original risk-parity research system under `research/`.

## Directory Map

- `scripts/run_platform_backtest.py`: platform backtest entrypoint.
- `scripts/run_platform_experiment.py`: standardized experiment runner with candidate/baseline comparison.
- `scripts/run_sim_portfolio.py`: create a simulated portfolio from a checkpoint; an existing `--portfolio-id` resumes saved state without requiring the initial checkpoint.
- `scripts/sync_platform_data.py`: sync platform market and fundamental data.
- `scripts/run_sensitivity.py`: start-date sensitivity analysis.
- `scripts/run_dashboard.py`: launch the local read-only browser dashboard (port defaults to 8501, override with the `PORT` environment variable).
- `scripts/run_live_cycle.py`: live-mirror portfolio entry — `reconcile` overwrites state from real holdings, `plan` renders the next-day order ticket, `cycle` chains sync/reconcile/plan/daily-valuation/notify and skips non-trading days (Task Scheduler command in the docstring). Each trading day the real holdings are marked to market into `real_nav.csv`, notifications are split into a markdown daily digest plus a separate ticket message when a rebalance triggers, and `--shadow` advances a shadow sim portfolio for attribution.
- `scripts/report_live_attribution.py`: monthly live-vs-shadow NAV attribution (cumulative diff, annualized tracking error, cash-drag vs execution-residual split; record-only). Reports land in `reports/live/`, which is gitignored because it contains real account values.
- `scripts/validate_hfq_data.py`: compare platform adjusted close against the research HFQ chain.
- `src/platform_core/`: platform engine package.
  - `models.py`: assets, bars, positions, orders, trades, portfolio state.
  - `engine.py`: daily event-driven backtest engine.
  - `execution.py`: target-weight execution, fees, lot sizing, suspension and price-limit checks.
  - `strategy.py`: platform strategy API and built-in strategies.
  - `data.py`, `data_store.py`, `data_sources.py`: local CSV data, normalization, and Finshare integration.
  - `metrics.py`: research-grade metrics computed from platform artifacts.
  - `visualization.py`: low-coupling chart rendering from persisted CSV artifacts.
  - `experiment.py`: experiment orchestration and report/archive writing.
  - `data_validation.py`: HFQ data-chain comparison helpers.
  - `sim.py`: simulated portfolio continuation from checkpoints.
  - `live.py`: live-mirror portfolio (mark-to-real reconcile + dry-run order-ticket planning + cycle orchestration; never simulates fills).
  - `notify.py`: push notifications (ServerChan/WeChat and SMTP; auto-enabled via RQ_SERVERCHAN_KEY or RQ_SMTP_* env vars; failures never break the flow).
  - `corporate_actions.py`: shared split loading and effective-date application for engine and sim.
  - `storage.py`: SQLite metadata store.
- `src/platform_dashboard/`: local read-only Streamlit dashboard.
  - `app.py`: page rendering (overview, run analysis, run comparison, strategy configs).
  - `artifacts.py`: artifact discovery and derived return analytics (`nav_analytics`, `rebase_benchmark`, `align_navs`, `window_start_date`).
- `configs/`: platform YAML configs.
- `data/`: platform-owned market data and SQLite metadata.
- `docs/`: current platform documentation and planned features.
- `reports/`: platform reports.
- `results/`: platform raw run artifacts.
- `tests/`: platform unit and integration tests.

## Commands

Run from the repository root:
Use `.\env\Scripts\python.exe` for venv/uv layouts, or substitute `.\env\python.exe` when the local environment exposes Python there.

```powershell
.\env\Scripts\python.exe platform\scripts\run_platform_backtest.py --config configs\domestic_rolling_bond_10y.yaml --start-date 2019-02-28 --end-date 2025-06-30
.\env\Scripts\python.exe platform\scripts\run_platform_backtest.py --config configs\domestic_ewma_bond_10y.yaml --start-date 2019-02-28 --end-date 2025-06-30
.\env\Scripts\python.exe platform\scripts\run_platform_experiment.py --config configs\domestic_rolling_bond_10y.yaml --start-date 2019-02-28 --end-date 2025-06-30
.\env\Scripts\python.exe platform\scripts\run_sensitivity.py --config configs\domestic_rolling_bond_10y.yaml --end-date 2025-06-30
.\env\Scripts\python.exe platform\scripts\validate_hfq_data.py --codes 510300 518880 511260
.\env\Scripts\python.exe platform\scripts\sync_platform_data.py --config configs\domestic_rolling_bond_10y.yaml
.\env\Scripts\python.exe platform\scripts\run_sim_portfolio.py --config configs\domestic_rolling_bond_10y.yaml --checkpoint <checkpoint.json> --asof-date 2026-05-30
.\env\Scripts\python.exe platform\scripts\run_dashboard.py
.\env\Scripts\python.exe platform\scripts\run_live_cycle.py reconcile --config configs\domestic_rolling_bond_10y.yaml --holdings <holdings.csv> --cash <float>
.\env\Scripts\python.exe platform\scripts\run_live_cycle.py plan --config configs\domestic_rolling_bond_10y.yaml
.\env\Scripts\python.exe platform\scripts\run_live_cycle.py cycle --config configs\domestic_rolling_bond_10y.yaml --sync --notify
```

The platform scripts change their working directory to `platform/`, so relative paths such as `configs/domestic_rolling_bond_10y.yaml`, `data/`, and `results/platform/` are platform-local.

All generated markdown reports should be written in Chinese. Keep exact config paths, commands, CSV column names, and metric keys unchanged when they are used as machine-readable identifiers.

## 研究验证规则

- 用户定向研究使用用户指定的窗口；回测、实验和敏感性命令默认 `standard`，运行 `default + stress` 两个场景。
- 起点敏感性默认每两个自然月生成一个起点；`--step` 只用于明确指定的交易日步长诊断，`--start-date` 和 `--end-date` 限定运行窗口。
- 自主选题与候选验收遵循根目录 `.agents/skills/run-autonomous-quant-research/SKILL.md`；`--slippage-scenario all` 显式运行三个执行场景。定向研究不自动套用自主研究样本划分或验收阈值。
- 对比报告展示实际指标及验证范围，候选结论依据所选研究流程、成本场景与敏感性证据判断。

## Implemented Capabilities

- Daily event loop with per-day checkpoints.
- Raw (unadjusted) price-based valuation and trade execution engine, which eliminates implicit compounding and cash drag.
- Corporate action modeling: share splits take effect on the first real bar date after `split_date` (prices reflect the split only from that day; see `corporate_actions.py` and `reports/split_effective_date_fix_report.md`), and cash dividends are recorded as `dividend_receivables` on `ex_date` and paid out on `payment_date`.
- Single target-weight strategy configuration per platform config (strategies calculate signals on smooth `adj_close`).
- Cash, position, cost-basis, pending-intent, and cooldown state.
- Fee, lot-size, suspension, limit-up, and limit-down execution checks.
- Retry, cancel, or mark-failed handling for unfilled intents.
- Built-in equal-weight, fundamental-filtered equal-weight, risk-parity, and EWMA risk-parity strategies.
- Point-in-time fundamental filtering where local fundamental data exists.
- SQLite metadata for strategy versions, backtests, checkpoints, simulated portfolios, and references.
- Standardized experiment reports with optional baseline comparison under `reports/experiments/`.
- Research-grade metrics: annualized return, volatility, max drawdown, Sharpe, turnover, trade/order counts, rejection counts, pending-intent pressure, and cash drag.
- CSV-only visualization module for NAV/drawdown, position weights, cash/pending-intent effects, and rejected-order reasons.
- Local Streamlit dashboard with four pages: overview, run analysis (net-value/return display with trailing-window rebasing, benchmark overlay and excess-return curve, monthly return heatmap, yearly returns, rolling volatility/Sharpe, training vs frozen-sample table, positions with cash layer, orders and trades), run comparison (2-5 runs re-normalized at the selected window start), and strategy configs.
- 起点敏感性使用每两个自然月一个起点；样本窗口由本次研究模式和运行参数决定，诊断可显式指定交易日步长。
- HFQ validation against the old research data chain.

## Archive Structure

- Fixed-config full-common-history backtests: `results/backtests/<run_id>/`
- Temporary direct backtests: `results/temporary_backtests/direct/<run_id>/`
- Raw standardized experiments: `results/temporary_backtests/experiments/<experiment>/<timestamp>/<strategy>/<run_id>/`
- Standardized experiment reports: `reports/experiments/<experiment>/<timestamp>/`
- Sensitivity raw runs: `results/sensitivity/<strategy>/<timestamp>/` (never loaded by Streamlit)
- Sensitivity reports: `reports/sensitivity/<strategy>/<timestamp>/`
- Data validation reports: `reports/data_validation/<timestamp>/`

Raw run directories contain execution-level artifacts. Report directories contain decision-level summaries, metrics, config copies, and pointers back to raw paths.
The Streamlit dashboard loads only fixed-config backtests by default. Its global sidebar option can additionally load temporary backtests. Training, final-test, experiment, sensitivity, generated-config, partial-window, and ad hoc runs must never be written to the fixed-config directory.

Direct runs record `artifact_provenance` in their manifest. A run enters `results/backtests/` only when its source matches a fixed config and its actual window matches the full common history. Older runs without this proof remain available through the temporary-backtest option; historical files are not moved or rewritten.

## Platform Docs

See `docs/current_platform.md` for the current effective platform design and `docs/planned_features.md` for planned features that are not fully implemented.

## Not Planned

- The old research strategy plugin interface `run_strategy(df, config)` will not be migrated. Platform strategies should use `Strategy.generate_targets(context)`.
