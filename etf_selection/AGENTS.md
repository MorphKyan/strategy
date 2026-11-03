# ETF Selection Instructions

## Scope

This directory owns ETF universe screening and basket construction. It may read platform market data, generate platform configs, and call platform CLI commands, but it remains independent of platform internals.

- Source: `src/`
- 正式配置：`configs/`；主入口为 `configs/etf_universe.yaml`。
- Entry: `.\env\Scripts\python.exe etf_selection\scripts\screen_etf_sleeves.py --config etf_selection\configs\etf_universe.yaml`
- 生成配置：`results/configs/<课题键>/<运行ID>/`，与 platform 使用相同目录结构。
- 最终研究及筛选报告：`reports/<课题键>/<发布版本>/report.md`。
- 自动筛选结果与运行摘要：`results/screening/<运行ID>/`。

最终报告布局见根 `AGENTS.md` 的“产物目录”；自动筛选与平台验证摘要默认写入所属子系统的 `results/`。

Use `.\env\python.exe` instead when that is the project's actual Python layout.

## Boundaries

- Do not put ETF selection code under `platform/` or modify the platform engine while screening ETFs.
- 不直接修改 platform 基线配置；生成配置只写入本子系统 `results/configs/<课题键>/<运行ID>/`，不进入 Git。
- Apply the root data freshness, research-mode, reporting, instrument-semantics, and artifact-preservation rules.
- If platform backtests are run, also read `platform/AGENTS.md`.

## Selection Workflow

1. Sync and verify freshness, alignment, adjusted-price inputs, and required liquidity fields for every candidate.
2. Screen candidates inside each sleeve, then check within-sleeve representative correlation.
3. Build cross-sleeve baskets and evaluate common history, cross-sleeve correlation, inverse-volatility concentration, liquidity, and data quality.
4. Use the history and research window specified by the user or config. Disclose short or uneven common history rather than silently changing the window.
5. 生成配置写入 `results/configs/<课题键>/<运行ID>/`，排名、相关性和篮子明细写入 `results/screening/<运行ID>/`。最终报告与可重建筛选和验证的脚本或配置放入 `reports/`；确认能够重新生成后清理中间产物，不长期存档。历史报告缺少生成入口时，只将必要原始 YAML 随报告保留在 `configs/` 附件目录，并标记完整复现未验证。
6. When platform validation is requested, use the root research mode: user-directed research runs `default` + `stress` and monthly start-date sensitivity; autonomous research follows `$run-autonomous-quant-research`.

## Default Sleeve Semantics

The default sleeves are `gold`, `hs300`, `commodity`, and `bond`.

- Prefer `subtype: broad` for commodity exposure.
- If no broad commodity ETF passes the applicable filters, multiple single-commodity ETFs may be used and disclosed.
- Keep gold in its own sleeve rather than treating it as commodity exposure.

Reports must include freshness and alignment results, filter outcomes, sleeve rankings, correlation results, basket components, sample window, score inputs, generated config paths, and exact platform commands and metrics when backtests are run.
