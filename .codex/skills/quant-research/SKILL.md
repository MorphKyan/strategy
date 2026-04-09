---
name: quant-research
description: Run one disciplined research cycle for this repository's risk-parity strategy workflow. Use when Codex needs to inspect the repo, propose a literature-supported low-complexity idea, delegate cleanly with subagents, run a backtest, and write a standardized experiment report without modifying the baseline strategy.
---

# Quant Research

Read `AGENTS.md` and `README_codex.md` before making changes.

Use this workflow:
1. Inspect the current baseline strategy, config, and backtest entrypoint.
2. Propose one or two low-complexity, literature-supported ideas adjacent to risk parity.
3. Use subagents when helpful:
   - `literature-scout`
   - `strategy-coder`
   - `backtest-runner`
   - `performance-reviewer`
4. Implement at most one high-confidence variant unless the user explicitly requests more.
5. Keep the baseline untouched and place new code under `src/strategies/`.
6. Run the standardized experiment command with `scripts/run_experiment.py` when a stable report is needed.
7. Save literature notes to `reports/literature/` when research is part of the task.
8. Save the experiment summary to `reports/experiments/`.

Output must include:
- concise hypothesis
- files changed
- exact command run
- key metrics versus baseline when available
- accept, reject, or refine recommendation
