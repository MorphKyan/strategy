# ETF Selection Agent Instructions

## Scope

This directory owns ETF universe screening and basket construction. It is a standalone research service that may generate platform configs and optionally call platform CLI commands.

The root `AGENTS.md` remains authoritative for workspace-wide rules, especially data freshness, fixed sample split, report language, cache reuse, and validation gates.

## Boundaries

- Do not put ETF selection code under `platform/` or `research/`.
- Do not modify platform engine or strategy code while screening ETFs.
- Do not modify platform baseline configs directly. Generated configs must be additive under `etf_selection/generated_configs/<timestamp>/`.
- The selector may read local platform market data and may call platform backtest commands, but platform remains an external runtime.
- ETF selection reports belong under `etf_selection/reports/<timestamp>/`.

## Main Workflow

1. Verify data freshness and alignment for every candidate symbol before screening.
2. Apply the fixed sample split before screening: ETF screening, ranking, basket construction, score comparison, correlations, inverse-vol concentration, and liquidity scores must use only data up to `2025-06-30`.
3. Screen ETFs inside each sleeve first.
4. Validate correlation inside each sleeve to find representative ETFs.
5. Build cross-sleeve baskets from shortlisted ETFs.
6. Validate cross-sleeve correlation and inverse-vol concentration.
7. Reject any basket whose common training history through `2025-06-30` is not longer than 3 years.
8. Write generated platform configs under `etf_selection/generated_configs/<timestamp>/`.
9. Write reports under `etf_selection/reports/<timestamp>/`.
10. If platform backtests are run, first run training-sample comparisons and start-date sensitivity. Only after the ETF basket and strategy choices are frozen may `2025-07-01` and later data be used for final testing.

## Sleeves

The default target sleeves are:

- `gold`
- `hs300`
- `commodity`
- `bond`

Commodity selection rule:

- Prefer broad commodity ETFs with `subtype: broad`.
- If no broad commodity ETF passes hard filters, allow multiple single-commodity ETFs with `subtype` values such as `single_energy`, `single_metals`, or `single_agriculture`.
- Do not treat gold as part of the commodity sleeve because gold has its own sleeve.

## Hard Filters

- Minimum local adjusted history is 3 years through the training-sample end date.
- Exclude assets with missing price or HFQ factor files unless the user explicitly asks to tolerate raw prices.
- Do not use `2025-07-01` or later data for research-stage rankings, basket scores, correlations, concentration checks, or acceptance thresholds.
- Keep all generated configs additive; never overwrite platform baseline configs.

## Scoring

Inside a sleeve, prefer:

- longer history
- stronger liquidity
- better data quality
- high representative correlation with peers in the same sleeve
- sane volatility relative to peers

Across sleeves, prefer:

- enough common history
- low cross-sleeve absolute correlation
- lower inverse-vol concentration
- acceptable liquidity
- stable execution when platform backtests are run

## Reporting

Reports must be written in Chinese, but keep machine-readable keys, file names, config paths, and metric names in ASCII. Every report should include:

- data freshness and alignment result
- hard filter results
- sleeve-level rankings
- sleeve correlation matrices
- generated basket configs
- basket score components
- confirmation that ETF screening and basket scoring used only data up to `2025-06-30`
- start-date sensitivity results when platform backtests are run
- final test-sample metrics for `2025-07-01` and later data, after the basket is frozen
- exact platform commands when backtests are run
