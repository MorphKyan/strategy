import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.platform_core.data_store import validate_market_dates


@pytest.fixture
def module():
    path = Path(__file__).parents[1] / "scripts/sync_pit_fundamental_views.py"
    spec = importlib.util.spec_from_file_location("pit_views", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_cpi_uses_actual_release_day_instead_of_assumed_tenth(module):
    releases = pd.DataFrame({"available_date": ["2023-12-09", "2024-01-12"], "cpi_yoy_pct": [-.5, -.3]})
    dates = pd.to_datetime(["2023-12-08", "2024-01-09", "2024-01-10", "2024-01-11", "2024-01-12"])
    result = module.observable_series(dates, releases, "cpi_yoy_pct") / 100
    assert pd.isna(result.iloc[0])
    assert result.iloc[1:].tolist() == pytest.approx([-.005, -.005, -.005, -.003])


def test_dividend_yield_does_not_borrow_another_funds_cash_distributions(module):
    prices = pd.Series(1., index=pd.date_range("2024-01-01", periods=2))
    dividends = pd.DataFrame({"code": ["510880"], "ex_date": ["2024-01-01"], "dividend_per_share": [.5]})
    assert module.compute_etf_dividend_yield_series("512890", prices, dividends).eq(0).all()


def test_dividend_yield_adjusts_old_distributions_to_current_share_units(module):
    prices = pd.Series([10., 10., 5.], index=pd.date_range("2024-01-01", periods=3))
    dividends = pd.DataFrame({"code": ["510300"], "ex_date": ["2024-01-01"], "dividend_per_share": [.2]})
    splits = pd.DataFrame({"code": ["510300"], "split_date": ["2024-01-02"], "split_ratio": [2.]})
    result = module.compute_etf_dividend_yield_series("510300", prices, dividends, splits)
    assert result.tolist() == pytest.approx([.02, .02, .02])


def test_roll_yield_uses_contract_expiries_and_next_market_day_availability(module):
    metadata = pd.DataFrame({"contract": ["M2405", "M2409"], "expiry_date": ["2024-05-20", "2024-09-18"]})
    dates = pd.date_range("2024-01-01", periods=3)

    def fetcher(symbol):
        return pd.DataFrame({"date": dates[:2], "settle": [100, 200] if symbol == "M2405" else [110, 110],
                             "hold": ["100", "100"] if symbol == "M2405" else ["9", "9"]})

    result = module.compute_real_futures_roll_yield_series("M", dates, metadata, fetcher)
    assert result.index.tolist() == list(dates[1:])
    days = (pd.Timestamp("2024-09-18") - pd.Timestamp("2024-05-20")).days
    assert result.tolist() == pytest.approx([-.1 * 365 / days, .45 * 365 / days])


def test_roll_yield_does_not_silently_accept_a_failed_contract_request(module):
    metadata = pd.DataFrame({"contract": ["M2405", "M2409"], "expiry_date": ["2024-05-20", "2024-09-18"]})
    with pytest.raises(RuntimeError, match="M2405"):
        module.compute_real_futures_roll_yield_series("M", pd.date_range("2024-01-01", periods=3), metadata,
                                                     lambda symbol: (_ for _ in ()).throw(OSError("offline")))


def test_generation_keeps_index_and_etf_units_separate_and_lags_bond_quotes(module, tmp_path):
    for code in ["000300", "CBA21801"]:
        pd.DataFrame({"trade_date": pd.date_range("2024-01-01", periods=3), "close": 3000}).to_csv(
            tmp_path / f"{code}.csv", index=False)
    macro = tmp_path / "fundamental_macro"
    macro.mkdir()
    pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "bond_ytm_30y": [4., 4.1, 4.2]}).to_csv(
        macro / "china_bond_yields_daily_pit.csv", index=False)
    yields = macro / "index_dividend_yield_releases.csv"
    pd.DataFrame({"symbol": ["000300", "000300"], "available_date": ["2024-01-02", "2024-01-03"],
                  "dividend_yield_pct": [2.5, 3.]}).to_csv(yields, index=False)
    result = module.generate_pit_views(tmp_path, ["000300", "CBA21801"])
    assert result[result["symbol"] == "000300"]["value"].tolist() == pytest.approx([.025, .03])
    assert result[result["symbol"] == "CBA21801"]["value"].tolist() == pytest.approx([.04, .041])
    assert set(result["trade_date"]) == {"2024-01-02", "2024-01-03"}


def test_partial_generation_preserves_unselected_symbols(module, tmp_path, monkeypatch):
    output = tmp_path / "views.csv"
    output.write_text("trade_date,symbol,metric,value\n2024-01-01,000300,dividend_yield,0.02\n")
    generated = pd.DataFrame({"trade_date": ["2024-01-02"], "symbol": ["CBA21801"], "metric": ["bond_ytm"], "value": [.04]})
    monkeypatch.setattr(module, "generate_pit_views", lambda *args, **kwargs: generated)
    monkeypatch.setattr(sys, "argv", ["sync", "--symbols", "CBA21801", "--output", str(output)])
    assert module.main() == 0
    assert pd.read_csv(output, dtype={"symbol": str})["symbol"].tolist() == ["000300", "CBA21801"]


def test_roll_yield_chooses_nearer_contract_when_open_interest_is_tied(module):
    contracts = pd.DataFrame({"contract": ["M2409", "M2405"], "expiry_date": ["2024-09-18", "2024-05-20"]})
    dates = pd.date_range("2024-01-01", periods=2)

    def fetcher(symbol):
        return pd.DataFrame({"date": dates[:1], "settle": [100 if symbol == "M2405" else 110], "hold": [10]})

    result = module.compute_real_futures_roll_yield_series("M", dates, contracts, fetcher)
    assert len(result) == 1 and result.iloc[0] < 0


def test_stale_market_snapshot_stops_pit_generation_before_contract_fetch(module, tmp_path, monkeypatch):
    monkeypatch.setattr("src.platform_core.data.validate_market_dates", validate_market_dates)
    pd.DataFrame({"trade_date": ["2020-01-01"], "close": [100]}).to_csv(tmp_path / "M0.csv", index=False)
    monkeypatch.setattr(module, "compute_real_futures_roll_yield_series", lambda *args: pytest.fail("不得继续抓取"))
    with pytest.raises(RuntimeError, match="Stale"):
        module.generate_pit_views(tmp_path, ["M0"])
