from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def synthetic_market_dates(monkeypatch):
    """合成历史夹具不参与当前快照门禁；门禁函数由独立测试直接覆盖。"""
    bypass = lambda latest, today: None
    monkeypatch.setattr("src.platform_core.data.validate_market_dates", bypass)
    monkeypatch.setattr("src.platform_core.data_store.validate_market_dates", bypass)
