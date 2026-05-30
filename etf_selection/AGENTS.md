# ETF Selection Agent Instructions

## Scope

This directory is for ETF universe screening and basket construction. Treat it as a standalone research service that can be owned by a dedicated agent.

## Boundaries

- Do not put ETF selection code under `platform/` or `research/`.
- Do not modify platform engine code when screening ETFs.
- Do not modify research risk-parity baseline files.
- The selector may read local market data and may generate platform configs.
- The selector may call platform CLI commands for backtests, but platform remains an external runtime.

## Main Workflow

1. Screen ETFs inside each sleeve first.
2. Validate correlation inside each sleeve to find representative ETFs.
3. Build cross-sleeve baskets from shortlisted ETFs.
4. Validate cross-sleeve correlation and inverse-vol concentration.
5. Write generated platform configs under `etf_selection/generated_configs/`.
6. Write reports under `etf_selection/reports/`.
7. Optionally call `platform/scripts/run_platform_experiment.py` to backtest generated configs.

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

- Minimum local adjusted history is 3 years.
- Exclude assets with missing price or HFQ factor files unless the user explicitly asks to tolerate raw prices.
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

- hard filter results
- sleeve-level rankings
- sleeve correlation matrices
- generated basket configs
- basket score components
- exact platform commands when backtests are run
