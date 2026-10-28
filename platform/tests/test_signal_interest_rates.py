"""Dynamic-rate timing, monthly signal integration and legacy compatibility."""
from types import SimpleNamespace
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.platform_core.interest_rates import SignalInterestRate, load_annual_rates, monthly_fast_slow_signal
from src.platform_core.strategies.expected_shortfall import RiskParityExpectedShortfallFixedBudgetStrategy as ES
from src.platform_core.strategy import StrategyContext


def write_rates(tmp_path, value=2.0):
    path = tmp_path / "rates.csv"
    pd.DataFrame({"date": pd.bdate_range("2022-11-01", "2024-03-29"), "annual_rate_pct": value}).to_csv(path, index=False)
    return path


def test_default_is_treasury_and_shibor_is_selectable(tmp_path):
    path = write_rates(tmp_path)
    assert SignalInterestRate({"path": path}).source == "treasury_3m"
    assert SignalInterestRate({"source": "shibor_1m", "path": path}).deduction("2024-01-31", "2024-02-29") == pytest.approx(.02 * 29 / 365)


def test_same_day_and_future_rates_are_excluded(tmp_path):
    path = write_rates(tmp_path)
    frame = pd.read_csv(path)
    frame.loc[frame.date >= "2024-01-31", "annual_rate_pct"] = 500
    frame.to_csv(path, index=False)
    rate = SignalInterestRate({"path": path})
    assert rate.deduction("2024-01-31", "2024-02-29") == pytest.approx(.02 * 29 / 365)


def test_missing_and_stale_rates_fail(tmp_path):
    path = write_rates(tmp_path)
    rate = SignalInterestRate({"path": path})
    for begin in ["2020-01-31", "2024-05-31"]:
        with pytest.raises(ValueError, match="Missing lagged"):
            rate.deduction(begin, "2024-06-30")
    with pytest.raises(FileNotFoundError):
        SignalInterestRate({"path": tmp_path / "missing.csv"})


@pytest.mark.parametrize("dates,values", [(["2024-01-01"] * 2, [1, 2]), (["2024-01-01"], [np.inf]), ([None], [2])])
def test_invalid_rate_csv_rejected(tmp_path, dates, values):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"date": dates, "annual_rate_pct": values}).to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_annual_rates(path)


def test_partial_month_and_future_price_do_not_change_signal(tmp_path):
    dates = pd.bdate_range("2023-01-01", "2024-03-29")
    prices = pd.Series(100., index=dates)
    rate = SignalInterestRate({"path": write_rates(tmp_path)})
    expected = monthly_fast_slow_signal(prices, "2024-03-15", rate, dates)
    prices.loc["2024-03-01":] = 10000
    assert monthly_fast_slow_signal(prices, "2024-03-15", rate, dates) == expected
    assert expected[0] == "bear"


@pytest.mark.parametrize("earlier,last,state", [(.01, .01, "bull"), (.01, -.01, "correction"), (-.01, .01, "rebound"), (-.01, -.01, "bear")])
def test_four_monthly_states(earlier, last, state):
    dates = pd.date_range("2023-01-31", periods=13, freq="ME")
    values = 100 * np.cumprod([1., *([1 + earlier] * 11), 1 + last])
    prices = pd.Series(values, index=dates)
    assert monthly_fast_slow_signal(prices, dates[-1], SignalInterestRate({"source": "fixed", "annual_rate": 0}))[0] == state


def test_missing_month_is_rejected():
    dates = pd.date_range("2022-12-31", periods=14, freq="ME").delete(5)
    with pytest.raises(ValueError, match="consecutive"):
        monthly_fast_slow_signal(pd.Series(100., index=dates), dates[-1], SignalInterestRate({"source": "fixed"}))


@pytest.mark.parametrize("source,expected", [("fixed", 1.0), ("treasury_3m", .25), ("shibor_1m", .25)])
def test_generate_targets_uses_configured_rate(tmp_path, monkeypatch, source, expected):
    dates = pd.bdate_range("2023-01-01", "2024-03-15")
    frame = pd.DataFrame({"A": 100., "B": 100.}, index=dates)
    data = SimpleNamespace(calendar=list(dates), get_price_frame=lambda *args, **kwargs: frame.copy())
    context = StrategyContext(
        date=dates[-1], assets={"A": None, "B": None}, bars={},
        state=SimpleNamespace(positions={}, cooldown_pool={}, last_date=None), data=data,
        params={"universe": ["A", "B"], "min_periods": 20, "rolling_window": 30,
                "risk_budgets": {"A": .5, "B": .5},
                "trend_filter_mode": "fast_slow", "trend_filter_assets": ["A"],
                "trend_filter_risk_free": {"source": source, "annual_rate": 0., "path": write_rates(tmp_path)}},
    )
    monkeypatch.setattr(ES, "_solve_expected_shortfall_risk_budget", staticmethod(lambda *a, **k: np.array([.5, .5])))
    strategy = ES()
    strategy.initialize(context)
    target = strategy.generate_targets(context)
    assert target.weights == pytest.approx({"A": .5 * expected, "B": .5})


def test_legacy_initialize_does_not_load_rate_files(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Legacy config must not load rates")
    monkeypatch.setattr("src.platform_core.strategies.expected_shortfall.SignalInterestRate", fail)
    for params in [{}, {"trend_filter_mode": "binary"}, {"trend_filter_mode": "aqr"}]:
        ES().initialize(StrategyContext(None, {}, {}, None, None, params))


def test_incomplete_signal_history_keeps_sleeve_in_cash(tmp_path):
    prices = pd.Series(100., index=pd.bdate_range("2024-01-01", "2024-03-15"))
    assert monthly_fast_slow_signal(prices, "2024-03-15", SignalInterestRate({"source": "fixed"})) is None


@pytest.mark.parametrize("config", [{"source": "dr007"}, {"source": "fixed", "annual_rate": -1}, {"source": "fixed", "annual_rate": float("nan")}, "shibor_1m"])
def test_invalid_config_rejected(config):
    with pytest.raises(ValueError):
        SignalInterestRate(config)


def test_import_preserves_history_and_rejects_conflicts(tmp_path):
    spec = importlib.util.spec_from_file_location("import_signal_rates", Path(__file__).parents[1] / "scripts/import_signal_interest_rates.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    incoming = tmp_path / "incoming.csv"
    incoming.write_text("date,annual_rate_pct\n2024-01-02,1.23\n")
    destination = module.import_rates("treasury_3m", incoming, tmp_path / "store")
    incoming.write_text("date,annual_rate_pct\n2024-01-03,1.24\n")
    module.import_rates("treasury_3m", incoming, destination.parent)
    stored = destination.read_bytes()
    assert len(load_annual_rates(destination)) == 2
    incoming.write_text("date,annual_rate_pct\n2024-01-02,99\n")
    with pytest.raises(ValueError, match="Conflicting"):
        module.import_rates("treasury_3m", incoming, destination.parent)
    assert destination.read_bytes() == stored
