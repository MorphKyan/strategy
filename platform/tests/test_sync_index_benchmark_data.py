from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync_index_benchmark_data.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("sync_index_benchmark_data", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _market_row(day: str, close: float) -> dict[str, object]:
    return {
        "trade_date": day,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": 0.0,
        "amount": 0.0,
        "adjust_factor": 1.0,
        "source": "chinabond_official",
        "updated_at": "2026-08-01T00:00:00",
    }


def test_merge_bounded_history_replaces_requested_window_and_preserves_earlier_rows(tmp_path):
    module = _load_script_module()
    out_path = tmp_path / "CBA21801.csv"
    pd.DataFrame(
        [_market_row("2012-12-31", 99.0), _market_row("2026-08-10", 250.0)]
    ).to_csv(out_path, index=False)
    fetched = pd.DataFrame(
        [_market_row("2013-01-02", 100.0), _market_row("2026-08-11", 251.0)]
    )

    merged = module._merge_bounded_history(
        out_path, fetched, start_date="20130101", end_date=None
    )

    assert merged["trade_date"].tolist() == [
        "2012-12-31",
        "2013-01-02",
        "2026-08-11",
    ]


def test_merge_bounded_history_replaces_same_day_with_fetched_value(tmp_path):
    module = _load_script_module()
    out_path = tmp_path / "CBA21801.csv"
    pd.DataFrame([_market_row("2026-08-11", 250.0)]).to_csv(out_path, index=False)
    fetched = pd.DataFrame([_market_row("2026-08-11", 251.0)])

    merged = module._merge_bounded_history(out_path, fetched, None, None)

    assert len(merged) == 1
    assert float(merged.iloc[0]["close"]) == 251.0


def test_fetch_chinabond_index_converts_api_timestamp_to_china_trade_date(monkeypatch):
    module = _load_script_module()

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            # 2011-01-03 16:00 UTC is 2011-01-04 00:00 in China.
            return {"CFZS_00": {"1294070400000": 100.2104}}

    class FakeSession:
        trust_env = True

        def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(module.requests, "Session", FakeSession)

    frame = module.fetch_chinabond_index("CBA21801")

    assert frame.iloc[0]["trade_date"] == "2011-01-04"
    assert float(frame.iloc[0]["close"]) == 100.2104
