from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.platform_core.strategies.black_litterman_es import RiskParityBlackLittermanStrategy
from src.platform_core.strategy import StrategyContext


def test_views_follow_configured_data_dir_and_preserve_symbol_zeros(tmp_path):
    directory = tmp_path / "fundamental_macro"
    directory.mkdir()
    path = directory / "pit_fundamental_views_daily.csv"
    path.write_text("trade_date,symbol,value\n2024-01-03,000300,0.02\n2024-01-02,000300,0.01\n")
    context = StrategyContext(None, {}, {}, None, SimpleNamespace(data_dir=tmp_path), {})
    strategy = RiskParityBlackLittermanStrategy()
    strategy.initialize(context)
    assert strategy._pit_views_df["symbol"].tolist() == ["000300", "000300"]
    assert strategy._pit_views_df["trade_date"].tolist() == list(pd.date_range("2024-01-02", periods=2))
    assert strategy._pit_views_df["value"].tolist() == [0.01, 0.02]


def test_corrupt_fundamental_views_are_not_silently_replaced_with_zero(tmp_path):
    directory = tmp_path / "fundamental_macro"
    directory.mkdir()
    (directory / "pit_fundamental_views_daily.csv").write_text("trade_date,symbol,value\ninvalid,000300,0.02\n")
    strategy = RiskParityBlackLittermanStrategy()
    with pytest.raises(ValueError):
        strategy.initialize(StrategyContext(None, {}, {}, None, SimpleNamespace(data_dir=tmp_path), {}))


@pytest.mark.parametrize("rows", ["2024-01-01,000300,inf\n", "2024-01-01,000300,nan\n",
                                  "2024-01-01,000300,0.1\n2024-01-01,000300,0.2\n"])
def test_nonfinite_or_duplicate_pit_views_fail_before_strategy_execution(tmp_path, rows):
    path = tmp_path / "fundamental_macro/pit_fundamental_views_daily.csv"
    path.parent.mkdir()
    path.write_text("trade_date,symbol,value\n" + rows)
    with pytest.raises(ValueError, match="PIT"):
        RiskParityBlackLittermanStrategy().initialize(
            StrategyContext(None, {}, {}, None, SimpleNamespace(data_dir=tmp_path), {}))


def _priced_context():
    codes = ["CN_INDEX:000300.SH", "CN_INDEX:000015.SH"]
    prices = pd.DataFrame(100 * np.exp(np.random.default_rng(42).normal(0, .01, (45, 2)).cumsum(axis=0)),
                          index=pd.bdate_range("2024-01-01", periods=45), columns=codes)
    return StrategyContext(prices.index[-1], {code: None for code in codes}, {}, None,
                           SimpleNamespace(get_price_frame=lambda *args, **kwargs: prices.copy()),
                           {"min_periods": 20, "rolling_window": 30})


def test_large_finite_pit_tilt_does_not_overflow_exponential():
    context = _priced_context()
    strategy = RiskParityBlackLittermanStrategy()
    strategy._pit_views_df = pd.DataFrame({"trade_date": [context.date], "symbol": ["000300"], "value": [1000.]})
    with np.errstate(over="raise", invalid="raise"):
        target = strategy._inverse_vol_target(context, list(context.assets))
    assert np.isfinite(list(target.weights.values())).all()
    assert target.weights["CN_INDEX:000300.SH"] > target.weights["CN_INDEX:000015.SH"]


def test_failed_optimization_does_not_return_equal_weights(monkeypatch):
    from src.platform_core.strategies import black_litterman_es

    context = _priced_context()
    strategy = RiskParityBlackLittermanStrategy()
    strategy._pit_views_df = None
    monkeypatch.setattr(black_litterman_es, "minimize", lambda *args, **kwargs: SimpleNamespace(
        success=False, x=np.full(2, .5)))
    with pytest.raises(RuntimeError, match="solver failed"):
        strategy._inverse_vol_target(context, list(context.assets))
