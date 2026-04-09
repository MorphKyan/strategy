---
name: quant-research
description: Run one disciplined research cycle for this repository's risk-parity strategy workflow. Use when Codex needs to inspect the repo, propose a literature-supported low-complexity idea, delegate cleanly with subagents, run a backtest, and write a standardized experiment report without modifying the baseline strategy.
---

# Quant Research

Read `AGENTS.md` and `README_codex.md` before making changes.

Use this workflow:
1. Inspect the current baseline strategy, config, and backtest entrypoint.
2. If basket choice is part of the research question, screen candidate China ETF baskets with `scripts/select_risk_parity_universe.py` before proposing strategy changes.
3. If important China ETFs are missing local data, try `scripts/select_risk_parity_universe.py --fetch-missing` before narrowing the basket.
4. Propose one or two low-complexity, literature-supported ideas adjacent to risk parity.
5. Use subagents when helpful:
   - `basket-selector`
   - `literature-scout`
   - `strategy-coder`
   - `backtest-runner`
   - `performance-reviewer`
6. Implement at most one high-confidence variant unless the user explicitly requests more.
7. Keep the baseline untouched and place new code under `src/strategies/`.
8. Keep basket experiments additive by generating new config files instead of overwriting `configs/risk_parity.yaml`.
9. Run `scripts/run_experiment.py` when a stable report is needed.
10. Save literature notes to `reports/literature/` when research is part of the task.
11. Save the experiment summary to `reports/experiments/`.

Output must include:
- concise hypothesis
- files changed
- exact command run
- basket rationale when the ETF combination changed
- key metrics versus baseline when available
- accept, reject, or refine recommendation
