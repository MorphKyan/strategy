# ETF Selection Instructions

## Scope

This directory owns ETF universe screening and basket construction. It may read platform market data, generate platform configs, and call platform CLI commands, but it remains independent of platform internals.

- Source: `src/`
- Main config: `config/etf_universe.yaml`
- Entry: `.\env\Scripts\python.exe etf_selection\scripts\screen_etf_sleeves.py --config etf_selection\config\etf_universe.yaml`
- Generated configs: `generated_configs/<timestamp>/`
- Reports: `reports/<timestamp>/`

Use `.\env\python.exe` instead when that is the project's actual Python layout.

## Boundaries

- Do not put ETF selection code under `platform/` or modify the platform engine while screening ETFs.
- Do not modify platform baseline configs directly. Generated configs must be additive under `generated_configs/<timestamp>/`.
- Apply the root data freshness, research-mode, reporting, instrument-semantics, and artifact-preservation rules.
- If platform backtests are run, also read `platform/AGENTS.md`.

## Selection Workflow

1. Sync and verify freshness, alignment, adjusted-price inputs, and required liquidity fields for every candidate.
2. Screen candidates inside each sleeve, then check within-sleeve representative correlation.
3. Build cross-sleeve baskets and evaluate common history, cross-sleeve correlation, inverse-volatility concentration, liquidity, and data quality.
4. Use the history and research window specified by the user or config. Disclose short or uneven common history rather than silently changing the window.
5. Write generated configs and Chinese reports under timestamped directories without overwriting prior outputs.
6. When platform validation is requested, use the root research mode: user-directed research runs `default` + `stress` and two-month start-date sensitivity; autonomous research follows `$run-autonomous-quant-research`.

## Default Sleeve Semantics

The default sleeves are `gold`, `hs300`, `commodity`, and `bond`.

- Prefer `subtype: broad` for commodity exposure.
- If no broad commodity ETF passes the applicable filters, multiple single-commodity ETFs may be used and disclosed.
- Keep gold in its own sleeve rather than treating it as commodity exposure.

Reports must include freshness and alignment results, filter outcomes, sleeve rankings, correlation results, basket components, sample window, score inputs, generated config paths, and exact platform commands and metrics when backtests are run.
