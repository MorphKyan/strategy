from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


def prepare_finshare_env(root: str | Path | None = None) -> None:
    base = Path(root) if root is not None else Path.cwd()
    local_home = base / ".finshare_home"
    local_logs = local_home / ".finshare" / "logs"
    local_appdata = local_home / "AppData" / "Roaming"
    local_logs.mkdir(parents=True, exist_ok=True)
    local_appdata.mkdir(parents=True, exist_ok=True)
    os.environ["HOME"] = str(local_home)
    os.environ["USERPROFILE"] = str(local_home)
    os.environ["APPDATA"] = str(local_appdata)


def patch_loguru_for_finshare() -> None:
    try:
        from loguru import logger as loguru_logger
    except ImportError:
        return

    if getattr(loguru_logger, "_platform_core_patch", False):
        return

    original_add = loguru_logger.add

    def safe_add(*args, **kwargs):
        kwargs["enqueue"] = False
        return original_add(*args, **kwargs)

    loguru_logger.add = safe_add
    loguru_logger._platform_core_patch = True


def _to_frame(value: Any) -> pd.DataFrame:
    if value is None:
        return pd.DataFrame()
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, list):
        rows = []
        for item in value:
            if hasattr(item, "model_dump"):
                rows.append(item.model_dump())
            elif hasattr(item, "__dict__"):
                rows.append(dict(item.__dict__))
            else:
                rows.append(item)
        return pd.DataFrame(rows)
    if isinstance(value, dict):
        return pd.DataFrame([value])
    if hasattr(value, "model_dump"):
        return pd.DataFrame([value.model_dump()])
    if hasattr(value, "__dict__"):
        return pd.DataFrame([dict(value.__dict__)])
    return pd.DataFrame()


class FinshareDataSource:
    def __init__(self, root: str | Path | None = None):
        prepare_finshare_env(root)
        patch_loguru_for_finshare()
        import finshare as fs

        self.fs = fs

    def fetch_bars(self, code: str, start: str | None = None, end: str | None = None, adjust: str | None = None) -> pd.DataFrame:
        frame = self.fs.get_historical_data(code, start=start, end=end, adjust=adjust)
        return _to_frame(frame)

    def fetch_financial_indicators(self, code: str, ann_date: str | None = None) -> pd.DataFrame:
        frame = self.fs.get_financial_indicator(code, ann_date=ann_date)
        return _to_frame(frame)


def today_iso() -> str:
    return date.today().isoformat()
