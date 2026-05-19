# ADR 0001: Platform Backtests Use a Daily Event Engine

Date: 2026-05-16

## Status

Accepted

## Context

The original repository is a research-oriented risk-parity backtest runner. The retail strategy platform needs richer account state than a price-matrix strategy can safely express: cash, positions, pending rebalance intents, cooldown pools, strategy versions, checkpoints, fees, and daily trading constraints.

## Decision

The platform core uses a daily event-driven engine as the canonical M0-M2 runtime. Existing research entrypoints remain unchanged. The new runtime is implemented in `src/platform_core/` and is invoked through `scripts/run_platform_backtest.py`.

## Consequences

- Strategy authors return target weights instead of raw fills.
- The execution layer owns order generation, fees, price-limit checks, and pending-intent retries.
- Every processed trading day can be checkpointed and resumed.
- Vectorized research can still be added later, but it will not replace the stateful platform engine.
