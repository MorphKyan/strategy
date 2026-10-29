from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


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

    merged = module.merge_chinabond_history(
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

    merged = module.merge_chinabond_history(out_path, fetched, None, None)

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


@pytest.mark.parametrize("kind", ["index", "futures", "bond"])
def test_bounded_sync_preserves_local_dates_absent_from_response(tmp_path, monkeypatch, kind):
    module = _load_script_module()
    monkeypatch.setattr(module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(module, "FUNDAMENTAL_DIR", tmp_path)
    days = ["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13"]
    if kind == "bond":
        path = tmp_path / "china_bond_yields_daily_pit.csv"
        pd.DataFrame({"date": days, "bond_ytm_30y": [2.0] * 4, "bond_ytm_10y": [1.5] * 4}).to_csv(path, index=False)
        monkeypatch.setattr(module.ak, "bond_zh_us_rate", lambda: pd.DataFrame({
            "日期": [days[2]], "中国国债收益率30年": [2.1], "中国国债收益率10年": [1.6],
        }))
        assert module.sync_pit_china_bond_ytm("20260811", "20260812")
        result = pd.read_csv(path)
        assert result["date"].tolist() == days
        assert result["bond_ytm_30y"].tolist() == [2.0, 2.0, 2.1, 2.0]
    else:
        code = "000300" if kind == "index" else "M0"
        path = tmp_path / f"{code}.csv"
        pd.DataFrame([_market_row(day, 100.0) for day in days]).to_csv(path, index=False)
        # Two-column futures input also guards against eager df.columns[4] fallback.
        columns = {"date": [days[2]], "close": [101.0]} if kind == "index" else {"日期": [days[2]], "收盘价": [101.0]}
        fetch_name = "stock_zh_index_daily" if kind == "index" else "futures_main_sina"
        monkeypatch.setattr(module.ak, fetch_name, lambda **kwargs: pd.DataFrame(columns))
        sync = module.sync_index_data if kind == "index" else module.sync_futures_main_data
        assert sync(code, "20260811", "20260812")
        result = pd.read_csv(path)
        assert result["trade_date"].tolist() == days
        assert result["close"].tolist() == [100.0, 100.0, 101.0, 100.0]
        assert result["adjust_factor"].tolist() == [1.0] * 4


@pytest.mark.parametrize("kind", ["index", "futures", "bond"])
@pytest.mark.parametrize("failure", ["empty", "outside_bounds", "nonfinite"])
def test_failed_sync_keeps_original_file_bytes(tmp_path, monkeypatch, kind, failure):
    module = _load_script_module()
    monkeypatch.setattr(module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(module, "FUNDAMENTAL_DIR", tmp_path)
    day = "2026-08-12"
    value = float("inf") if failure == "nonfinite" else 100.0
    rows = [] if failure == "empty" else [day]
    if kind == "bond":
        path = tmp_path / "china_bond_yields_daily_pit.csv"
        old = pd.DataFrame({"date": [day], "bond_ytm_30y": [2.0], "bond_ytm_10y": [1.5]})
        fetched = pd.DataFrame({"日期": rows, "中国国债收益率30年": [value] * len(rows), "中国国债收益率10年": [1.5] * len(rows)})
        monkeypatch.setattr(module.ak, "bond_zh_us_rate", lambda: fetched)
        sync = module.sync_pit_china_bond_ytm
    else:
        code = "000300" if kind == "index" else "M0"
        path = tmp_path / f"{code}.csv"
        old = pd.DataFrame([_market_row(day, 100.0)])
        fetched = pd.DataFrame({"date": rows, "close": [value] * len(rows)})
        fetch_name = "stock_zh_index_daily" if kind == "index" else "futures_main_sina"
        monkeypatch.setattr(module.ak, fetch_name, lambda **kwargs: fetched)
        sync_fn = module.sync_index_data if kind == "index" else module.sync_futures_main_data
        sync = lambda start, end: sync_fn(code, start, end)
    old.to_csv(path, index=False)
    original = path.read_bytes()
    start = "20260813" if failure == "outside_bounds" else None
    assert not sync(start, None)
    assert path.read_bytes() == original


@pytest.mark.parametrize("close", [0., -1., float("inf")])
def test_official_index_rejects_bad_levels_before_they_can_replace_history(monkeypatch, close):
    module = _load_script_module()
    response = type("Response", (), {"raise_for_status": lambda self: None,
                                    "json": lambda self: {"CFZS_00": {"1294070400000": close}}})()
    monkeypatch.setattr(module.requests, "Session", lambda: type(
        "Session", (), {"post": lambda *args, **kwargs: response})())
    with pytest.raises(ValueError, match="positive"):
        module.fetch_chinabond_index("CBA21801")


def test_standalone_chinabond_entry_preserves_newer_snapshot(tmp_path, monkeypatch):
    import sys

    monkeypatch.chdir(Path.cwd())
    spec = importlib.util.spec_from_file_location("fetch_chinabond_30y", SCRIPT_PATH.with_name("fetch_chinabond_30y.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / "CBA21801.csv"
    pd.DataFrame([_market_row("2026-08-13", 101.)]).to_csv(path, index=False)
    original = path.read_bytes()
    monkeypatch.setattr(module, "fetch_chinabond_index", lambda *args, **kwargs: pd.DataFrame([
        _market_row("2026-08-12", 100.)]))
    monkeypatch.setattr(sys, "argv", ["fetch", "--data-dir", str(tmp_path)])
    assert module.main() == 1
    assert path.read_bytes() == original


@pytest.mark.parametrize("bad_row", [{"invalid_timestamp": 100.}, {"1294070400000": None}, {"1294070400000": "nan"}])
def test_partial_bad_official_snapshot_cannot_delete_a_date_inside_requested_window(tmp_path, monkeypatch, bad_row):
    module = _load_script_module()
    monkeypatch.setattr(module, "DATA_DIR", tmp_path)
    path = tmp_path / "CBA21801.csv"
    pd.DataFrame([_market_row("2011-01-04", 100.), _market_row("2011-01-05", 101.)]).to_csv(path, index=False)
    original = path.read_bytes()
    response = type("Response", (), {"raise_for_status": lambda self: None,
                                    "json": lambda self: {"CFZS_00": {**bad_row, "1294156800000": 101.}}})()
    monkeypatch.setattr(module.requests, "Session", lambda: type(
        "Session", (), {"post": lambda *args, **kwargs: response})())
    assert not module.sync_index_data("CBA21801", "20110104", "20110105")
    assert path.read_bytes() == original
