---
name: run-autonomous-quant-research
description: Run the repository's strict autonomous quant-research protocol when agents select or claim research directions themselves, including fixed sample isolation, candidate freeze, three slippage scenarios, sensitivity analysis, evidence capture, and independent review. Use only for explicitly requested autonomous/self-directed research or when another repository skill or agent harness explicitly invokes it. Do not use for user-defined research directions, ordinary historical scenario analysis, or routine platform engineering.
---

# Run Autonomous Quant Research

Use this protocol only for autonomous research. Read the root `AGENTS.md` and the closest subsystem `AGENTS.md`; this skill adds stricter research gates without replacing them.

## Fixed Research Design

- Training/research sample: all permitted data through `2025-06-30`.
- Final test sample: data from `2025-07-01` onward.
- Do not use final-test information to form hypotheses, select assets, choose parameters, set thresholds, filter candidates, or decide whether to reuse research caches.
- Require more than three years of common history through `2025-06-30` before submitting a platform config or ETF basket.
- Freeze the strategy, parameters, instruments, rebalance rules, baselines, and acceptance thresholds before the first final-test run. Do not revise the candidate after seeing final-test results.

## Topic Selection

1. Check `research-dashboard/pull_requests/` for unresolved `PR_*.md` handoffs before starting new work.
2. Read the backlog, research history, relevant platform reports, current strategies, and ETF configs to avoid duplicates.
3. Support hypotheses with citable sources and explain how the repository can validate them.
4. Prefer ideas adjacent to risk parity: volatility estimation, robust covariance, volatility targeting, rebalance rules, turnover controls, and ETF basket selection.
5. Treat deep learning, reinforcement learning, broad factor models, large parameter searches, and unrelated architecture changes as non-default exploratory work unless the user explicitly requests them.
6. Record validation cost, risks, failure conditions, and why a high-uncertainty topic must not be merged directly.

## Research and Validation

1. Claim the backlog item and record owner/session before implementation.
2. Create and maintain a research note from `research-dashboard/research_note_template.md`.
3. Confirm the relevant baseline and candidate scope before running comparisons.
4. Run training comparisons capped at `2025-06-30` for all three scenarios: `default`, `stress`, and `dynamic_participation`.
5. Run start-date sensitivity from the earliest common training date through `2025-06-30`, using one runtime start date every 2 calendar months, for all three scenarios.
6. Use generated, demo, or archived configs only when the claim depends on them or the user asks. For strategy variants, cover the relevant active baselines and every config intended to use the variant. For ETF sleeve expansion, validate across multiple appropriate built-in strategies.
7. Reuse a cache only when symbols, config hash or parameters, sample window, data snapshot, code version, and slippage scenario match. Never use final-test data or an older pre-sync snapshot for a research decision.
8. After the candidate and thresholds are frozen, run final-test validation from `2025-07-01` onward for all three scenarios.
9. Verify raw artifacts and standardized reports exist. Read metrics from actual artifacts.

Report per scenario:

- annualized return and volatility;
- Sharpe and max drawdown;
- annualized turnover;
- trade, order, and rejection counts;
- pending-intent pressure, cash drag, execution slippage, and other available task-relevant metrics.

State whether ranking and material metrics change across start dates and scenarios. Do not average scenarios in a way that hides a failure.

## Acceptance and Cleanup

Recommend a candidate only when training comparison passes, sensitivity is stable, final testing remains acceptable versus baseline, and execution risk is acceptable in all three scenarios.

Mark the result `Failed` or `research-only` when it is locally advantageous, unstable, overfit, fails final testing, or increases annualized two-sided turnover by more than 30% without clear compensating benefit. Remove failed/research-only strategy registrations and candidate configs from the submitted diff, while preserving research notes, reports, and historical artifacts.

Update the backlog, research note, standard Chinese report, and research history. Include the hypothesis, files changed, exact commands, baseline/candidate metrics, sensitivity, final-test metrics, scenario comparisons, artifact paths, and recommendation.

## Independent Review

Have a reviewer who did not select or implement the candidate inspect the evidence read-only. The reviewer must verify sample isolation, freeze order, data freshness, cache provenance, artifact traceability, metric completeness, three-scenario coverage, hidden benchmark changes, overfitting, and cleanup. The result must be `Accept`, `Reject`, `Needs Fix`, or `Research-only`.
