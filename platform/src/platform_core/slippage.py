from __future__ import annotations

import copy
from typing import Any


SLIPPAGE_SCENARIOS: dict[str, dict[str, Any]] = {
    "default": {
        "default_bps": 2.0,
        "qdii_commodity_bps": 6.0,
        "participation_impact": {"enabled": False},
    },
    "stress": {
        "default_bps": 10.0,
        "qdii_commodity_bps": 30.0,
        "participation_impact": {"enabled": False},
    },
    "dynamic_participation": {
        "default_bps": 2.0,
        "qdii_commodity_bps": 6.0,
        "participation_impact": {
            "enabled": True,
            "free_participation_rate": 0.005,
            "impact_bps_per_1pct": 5.0,
            "max_impact_bps": 100.0,
            "missing_amount_extra_bps": 20.0,
        },
    },
}


REQUIRED_SLIPPAGE_SCENARIOS = tuple(SLIPPAGE_SCENARIOS.keys())


def apply_slippage_scenario(config: dict[str, Any], scenario: str) -> dict[str, Any]:
    if scenario not in SLIPPAGE_SCENARIOS:
        raise ValueError(f"Unknown slippage scenario: {scenario}")
    runtime = copy.deepcopy(config)
    runtime.setdefault("execution", {})["slippage_scenario"] = scenario
    runtime["execution"]["slippage"] = copy.deepcopy(SLIPPAGE_SCENARIOS[scenario])
    platform = runtime.setdefault("platform", {})
    base_name = platform.get("run_name", "platform_backtest")
    platform["run_name"] = f"{base_name}_{scenario}"
    return runtime

