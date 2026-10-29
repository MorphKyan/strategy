from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import validate_market_dates
from src.platform_core.engine import PlatformBacktestEngine
from src.platform_core.execution import ExecutionConfig, ExecutionEngine, FeeProfile
from src.platform_core.models import Asset, Bar, PortfolioState, TargetPortfolio
from src.platform_core.storage import InMemoryStore


def test_unsorted_quotes_do_not_fill_hfq_factors_from_future(tmp_path):
    pd.DataFrame({"trade_date": ["2024-01-03", "2024-01-02", "2024-01-01"],
                  "close": [10, 10, 10], "volume": [1, 1, 1]}).to_csv(tmp_path / "A.csv", index=False)
    pd.DataFrame({"trade_date": ["2024-01-01", "2024-01-03"], "hfq_factor": [1, 2]}).to_csv(
        tmp_path / "A_hfq_factor.csv", index=False)
    data = LocalCsvBarData(tmp_path, [Asset("A", "A", "A")])
    assert data.frames["A"]["adj_close"].tolist() == [10, 10, 20]


def test_factor_before_first_quote_is_retained_without_borrowing_future_factor(tmp_path):
    pd.DataFrame({"trade_date": ["2024-01-02", "2024-01-03"], "close": 10}).to_csv(tmp_path / "A.csv", index=False)
    pd.DataFrame({"trade_date": ["2024-01-01", "2024-01-04"], "hfq_factor": [2, 3]}).to_csv(
        tmp_path / "A_hfq_factor.csv", index=False)
    data = LocalCsvBarData(tmp_path, [Asset("A", "A", "A")])
    assert data.frames["A"]["adj_close"].tolist() == [20, 20]


def test_missing_quote_date_is_rejected_before_calendar_construction(tmp_path):
    pd.DataFrame({"trade_date": ["2024-01-02", None], "close": 10}).to_csv(tmp_path / "A.csv", index=False)
    with pytest.raises(ValueError, match="Missing trade_date"):
        LocalCsvBarData(tmp_path, [Asset("A", "A", "A")])


def test_calendar_lookups_keep_strict_split_dates_and_suspended_gap_prices(tmp_path):
    pd.DataFrame({"trade_date": ["2024-01-30", "2024-02-02"], "close": [10, 20], "volume": 100}).to_csv(
        tmp_path / "A.csv", index=False)
    data = LocalCsvBarData(tmp_path, [Asset("A", "A", "A")])
    assert data.first_bar_date_after("A", date(2024, 1, 29)) == date(2024, 1, 30)
    assert data.first_bar_date_after("A", date(2024, 1, 30)) == date(2024, 2, 2)
    assert data.first_bar_date_after("A", date(2024, 2, 2)) is None
    assert not data.bars_on(date(2024, 1, 29))
    bar = data.bars_on(date(2024, 1, 31))["A"]
    assert bar.is_suspended and bar.close == 10
    assert data.is_month_end(date(2024, 1, 30))
    assert not data.is_month_end(date(2024, 1, 31))
    assert not data.is_month_end(date(2024, 2, 3))


def test_bounded_window_retains_previous_close_for_first_day_limits(tmp_path):
    pd.DataFrame({"trade_date": ["2024-01-02", "2024-01-03"], "close": [10, 11], "volume": 100}).to_csv(
        tmp_path / "A.csv", index=False)
    data = LocalCsvBarData(tmp_path, [Asset("A", "A", "A")], start_date="2024-01-03")
    bar = data.bars_on(date(2024, 1, 3))["A"]
    assert bar.limit_up == 11
    state = PortfolioState(cash=10000)
    execution = ExecutionEngine(ExecutionConfig(fee_profile=FeeProfile()))
    orders, trades = execution.apply_target(bar.date, state, data.assets, {"A": bar}, TargetPortfolio({"A": 1}))
    assert not trades and orders[0].reason == "limit_up"


def test_historical_window_still_checks_complete_local_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr("src.platform_core.data.validate_market_dates", validate_market_dates)
    monkeypatch.setattr("src.platform_core.data.date", SimpleNamespace(today=lambda: date(2026, 10, 29)))
    for code, days in [("A", ["2026-10-27", "2026-10-28"]), ("B", ["2026-10-27", "2026-10-28", "2026-10-29"])]:
        pd.DataFrame({"trade_date": days, "close": 10}).to_csv(tmp_path / f"{code}.csv", index=False)
    with pytest.raises(RuntimeError, match="not aligned"):
        LocalCsvBarData(tmp_path, [Asset(code, code, code) for code in "AB"], end_date="2026-10-27")


def test_backtest_rejects_empty_runtime_window_before_writing_results(tmp_path):
    pd.DataFrame({"trade_date": ["2024-01-01"], "close": [10]}).to_csv(tmp_path / "A.csv", index=False)
    config = {"data": {"data_dir": str(tmp_path)}, "assets": [{"asset_id": "A", "code": "A"}],
              "strategy": {"strategy_name": "monthly_equal_weight"},
              "backtest": {"start_date": "2023-01-01", "end_date": "2023-01-31"},
              "output": {"results_dir": str(tmp_path / "results")}}
    with pytest.raises(ValueError, match="runtime window"):
        PlatformBacktestEngine(config, InMemoryStore())
    assert not (tmp_path / "results").exists()


@pytest.mark.parametrize("price", [0, -1, float("inf")])
def test_invalid_close_prices_stop_loading(tmp_path, price):
    pd.DataFrame({"trade_date": ["2024-01-01"], "close": [price]}).to_csv(tmp_path / "A.csv", index=False)
    with pytest.raises(ValueError, match="close"):
        LocalCsvBarData(tmp_path, [Asset("A", "A", "A")])


@pytest.mark.parametrize("field", ["amount", "volume"])
@pytest.mark.parametrize("value", [-1, float("inf")])
def test_invalid_liquidity_stops_loading(tmp_path, field, value):
    pd.DataFrame({"trade_date": ["2024-01-01"], "close": [10], field: [value]}).to_csv(
        tmp_path / "A.csv", index=False)
    with pytest.raises(ValueError, match=field):
        LocalCsvBarData(tmp_path, [Asset("A", "A", "A")])


@pytest.mark.parametrize("opening", [0, float("nan")])
def test_suspended_asset_without_open_quote_still_rejects_order(opening):
    bar = Bar(date(2024, 1, 1), "A", opening, 10, 10, 10, is_suspended=True)
    state = PortfolioState(cash=1000)
    engine = ExecutionEngine(ExecutionConfig(fee_profile=FeeProfile()))
    orders, trades = engine.apply_target(bar.date, state, {"A": Asset("A", "A", "A", lot_size=1)},
                                         {"A": bar}, TargetPortfolio({"A": 1}))
    assert not trades
    assert orders[0].reason == "suspended"
    assert state.cash == 1000


@pytest.mark.parametrize("opening", [0, float("nan"), float("inf")])
def test_invalid_execution_price_fails_before_changing_state(opening):
    bar = Bar(date(2024, 1, 1), "A", opening, 10, 10, 10)
    state = PortfolioState(cash=1000)
    before = state.to_dict()
    engine = ExecutionEngine(ExecutionConfig(fee_profile=FeeProfile()))
    with pytest.raises(ValueError, match="price"):
        engine.apply_target(bar.date, state, {"A": Asset("A", "A", "A")}, {"A": bar}, TargetPortfolio({"A": 1}))
    assert state.to_dict() == before
