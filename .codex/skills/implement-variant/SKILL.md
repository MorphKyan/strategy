---
name: implement-variant
description: Implement one additive strategy variant with minimal diff in this repository. Use when Codex needs to create a new risk-parity-related strategy file under src/strategies, keep compatibility with main.py, and avoid modifying the baseline implementation.
---

# Implement Variant

Use this workflow:
1. Read the baseline strategy interface in `src/strategies/risk_parity.py`.
2. Create exactly one new strategy module under `src/strategies/`.
3. Reuse the current config shape unless a new config is necessary.
4. Keep the variant compatible with `main.py` dynamic import behavior.
5. Avoid unrelated cleanup or broad refactors.
6. If a validation command exists, run it after the change.

Return:
- variant name
- files changed
- rationale
- assumptions or risks
