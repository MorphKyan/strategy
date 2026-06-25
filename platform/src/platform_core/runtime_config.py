from __future__ import annotations

import copy
from typing import Any


def apply_runtime_dates(config: dict[str, Any], start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    runtime = copy.deepcopy(config)
    if start_date is not None or end_date is not None:
        backtest = runtime.get("backtest") or {}
        runtime["backtest"] = backtest
        if start_date is not None:
            backtest["start_date"] = start_date
        if end_date is not None:
            backtest["end_date"] = end_date
    return runtime
