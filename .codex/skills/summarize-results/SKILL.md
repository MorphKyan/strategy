---
name: summarize-results
description: Summarize experiment outcomes for this repository in a consistent markdown report. Use when Codex needs to compare baseline and variant metrics from standardized artifacts and produce a clear accept, reject, or refine recommendation under reports/experiments.
---

# Summarize Results

Use this workflow:
1. Read the latest standardized metrics for the baseline and the candidate strategy.
2. Compare only metrics that actually exist.
3. Write a markdown report under `reports/experiments/`.
4. Include:
   - experiment goal
   - hypothesis
   - implementation notes
   - exact backtest commands
   - metric comparison
   - recommendation

Decision policy:
- reject when out-of-sample results materially worsen
- reject when turnover rises sharply without strong compensating benefit
- prefer stable improvements over marginal in-sample gains
- say explicitly when a metric is unavailable
