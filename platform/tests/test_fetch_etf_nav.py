import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml


@pytest.fixture
def nav_module(monkeypatch):
    monkeypatch.chdir(Path.cwd())
    module = importlib.import_module("scripts.fetch_etf_nav")
    monkeypatch.setattr(module.time, "sleep", lambda *args: None)
    return module


def _session(pages):
    pages = iter(pages)

    def get(*args, **kwargs):
        payload = next(pages)
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: payload)

    return SimpleNamespace(get=get)


def _row(day, unit="1", cum="1"):
    return {"FSRQ": day, "DWJZ": unit, "LJJZ": cum}


def _page(total, rows):
    return {"TotalCount": total, "Data": {"LSJZList": rows}}


def test_nav_requires_complete_unique_pagination(nav_module):
    pages = [_page(3, [_row("2024-01-03"), _row("2024-01-02")]), _page(3, [_row("2024-01-01")])]
    frame = nav_module.fetch_nav("513100", _session(pages))
    assert frame["trade_date"].astype(str).tolist() == ["2024-01-01", "2024-01-02", "2024-01-03"]


@pytest.mark.parametrize("pages", [
    [_page(None, [_row("2024-01-01")])],
    [_page(3, [_row("2024-01-02")]), _page(3, [])],
    [_page(2, [_row("2024-01-01")]), _page(2, [_row("2024-01-01")])],
    [_page(2, [_row("2024-01-01")]), _page(3, [_row("2024-01-02")])],
])
def test_missing_counts_truncated_repeated_or_changed_pages_are_rejected(nav_module, pages):
    with pytest.raises((RuntimeError, ValueError)):
        nav_module.fetch_nav("513100", _session(pages))


@pytest.mark.parametrize("unit,cum", [("0", "1"), ("-1", "1"), ("inf", "1"), ("nan", "1"), ("1", "nan")])
def test_invalid_nav_values_are_not_silently_dropped(nav_module, unit, cum):
    with pytest.raises(ValueError):
        nav_module.fetch_nav("513100", _session([_page(1, [_row("2024-01-01", unit, cum)])]))


def test_history_guard_detects_lost_dates_even_when_row_count_and_latest_increase(tmp_path, nav_module):
    path = tmp_path / "513100.csv"
    pd.DataFrame({"trade_date": ["2024-01-01", "2024-01-03"]}).to_csv(path, index=False)
    with pytest.raises(RuntimeError, match="历史日期"):
        nav_module.guard_history_shrink(path, pd.DataFrame({"trade_date": ["2024-01-02", "2024-01-03", "2024-01-04"]}))


def test_config_nav_codes_include_etfs_only(tmp_path, nav_module):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"assets": [{"asset_id": "A", "code": "513100"},
                                               {"asset_id": "I", "code": "000300", "asset_type": "index"}]}))
    assert nav_module.codes_from_config(path) == ["513100"]


def test_report_uses_observable_premium_and_failed_fetch_preserves_original(tmp_path, nav_module, monkeypatch, capsys):
    days = pd.date_range("2024-01-01", periods=5)
    pd.DataFrame({"trade_date": days, "close": [100.] * 5}).to_csv(tmp_path / "513100.csv", index=False)
    frame = pd.DataFrame({"trade_date": days.date, "unit_nav": [1., 1., 1., 50., 100.], "cum_nav": [1., 1., 1., 50., 100.]})
    monkeypatch.setattr(nav_module, "fetch_nav", lambda *args: frame.copy())
    monkeypatch.setattr(nav_module, "_session", lambda: None)
    monkeypatch.setattr(sys, "argv", ["nav", "--codes", "513100", "--data-dir", str(tmp_path), "--report"])
    assert nav_module.main() == 0
    output = capsys.readouterr().out
    assert "观测 2024-01-03" in output and "最新 9900.00%" in output
    path = tmp_path / "etf_nav/513100.csv"
    original = path.read_bytes()

    def fail(*args):
        raise RuntimeError("pagination failed")

    monkeypatch.setattr(nav_module, "fetch_nav", fail)
    assert nav_module.main() == 1
    assert path.read_bytes() == original


def test_unavailable_report_is_a_reported_failure_instead_of_an_uncaught_exception(tmp_path, nav_module, monkeypatch):
    days = pd.date_range("2024-01-01", periods=2)
    pd.DataFrame({"trade_date": days, "close": [100., 101.]}).to_csv(tmp_path / "513100.csv", index=False)
    frame = pd.DataFrame({"trade_date": days.date, "unit_nav": [1., 1.], "cum_nav": [1., 1.]})
    monkeypatch.setattr(nav_module, "fetch_nav", lambda *args: frame.copy())
    monkeypatch.setattr(nav_module, "_session", lambda: None)
    monkeypatch.setattr(sys, "argv", ["nav", "--codes", "513100", "--data-dir", str(tmp_path), "--report"])
    assert nav_module.main() == 1
    assert (tmp_path / "etf_nav/513100.csv").exists()
