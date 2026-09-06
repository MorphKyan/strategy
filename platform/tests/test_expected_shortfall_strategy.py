from __future__ import annotations

import numpy as np
import pytest

import pandas as pd
from src.platform_core.strategy import StrategyContext, get_strategy_class
from src.platform_core.strategies.expected_shortfall import (
    RiskParityExpectedShortfallFixedBudgetStrategy,
)


def test_expected_shortfall_fixed_budget_strategy_is_registered():
    assert (
        get_strategy_class("risk_parity_expected_shortfall_fixed_budget")
        is RiskParityExpectedShortfallFixedBudgetStrategy
    )


def test_expected_shortfall_solver_matches_linear_loss_risk_budgets():
    returns = np.tile(np.asarray([-0.02, -0.01, -0.005]), (120, 1))
    budgets = np.asarray([0.45, 0.25, 0.30])

    weights = RiskParityExpectedShortfallFixedBudgetStrategy._solve_expected_shortfall_risk_budget(
        returns,
        budgets,
        confidence_level=0.95,
    )

    expected = budgets / np.asarray([0.02, 0.01, 0.005])
    expected /= expected.sum()
    assert weights == pytest.approx(expected, abs=1e-5)
    assert weights.sum() == pytest.approx(1.0)


def test_expected_shortfall_solver_rejects_budget_dimension_mismatch():
    returns = np.full((120, 3), -0.01)
    with pytest.raises(ValueError, match="Risk budget count"):
        RiskParityExpectedShortfallFixedBudgetStrategy._solve_expected_shortfall_risk_budget(
            returns,
            np.asarray([0.5, 0.5]),
            confidence_level=0.95,
        )


def test_filtered_historical_scenarios_rescale_past_shocks_to_latest_volatility():
    calm_then_volatile = np.asarray(
        [[0.001, -0.002], [-0.001, 0.002], [0.001, -0.001], [0.03, -0.04]]
    )

    filtered = RiskParityExpectedShortfallFixedBudgetStrategy._expected_shortfall_scenarios(
        calm_then_volatile,
        method="filtered",
        fhs_decay=0.94,
    )

    assert filtered.shape == calm_then_volatile.shape
    assert np.all(np.isfinite(filtered))
    assert not np.allclose(filtered, calm_then_volatile)


def test_expected_shortfall_scenarios_reject_unknown_method():
    with pytest.raises(ValueError, match="es_method"):
        RiskParityExpectedShortfallFixedBudgetStrategy._expected_shortfall_scenarios(
            np.full((10, 2), 0.001),
            method="unknown",
        )


def test_empirical_es_uses_fractional_tail_mass():
    returns = np.asarray([[-4.0], [-3.0], [-2.0], [-1.0]])

    value, gradient = RiskParityExpectedShortfallFixedBudgetStrategy._empirical_es_and_gradient(
        returns,
        np.asarray([1.0]),
        confidence_level=0.625,
    )

    assert value == pytest.approx((4.0 + 0.5 * 3.0) / 1.5)
    assert gradient == pytest.approx([(4.0 + 0.5 * 3.0) / 1.5])


def test_expected_shortfall_continuous_trend_filter_scaling():
    rng = np.random.RandomState(42)
    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    ret_a = rng.normal(0.0005, 0.01, size=60)
    ret_b = rng.normal(0.0005, 0.01, size=60)
    prices_a = 10.0 * np.cumprod(1.0 + ret_a)
    prices_b = 10.0 * np.cumprod(1.0 + ret_b)
    # Ensure asset A is clearly above rolling mean and asset B is below
    prices_a[-1] = prices_a[-20:].mean() + 3.0 * prices_a[-20:].std()
    prices_b[-1] = prices_b[-20:].mean() - 3.0 * prices_b[-20:].std()
    df = pd.DataFrame({"A": prices_a, "B": prices_b}, index=dates)

    class MockDataStore:
        def get_price_frame(self, universe, date, use_nav=False):
            return df.copy()

    strategy = RiskParityExpectedShortfallFixedBudgetStrategy()
    context = StrategyContext(
        date=dates[-1],
        assets={},
        bars={},
        state=None,
        data=MockDataStore(),
        params={
            "rolling_window": 30,
            "min_periods": 20,
            "risk_budgets": {"A": 0.5, "B": 0.5},
            "trend_filter_window": 20,
            "trend_filter_mode": "continuous",
        },
    )

    targets = strategy._inverse_vol_target(context, ["A", "B"])
    assert targets is not None
    assert targets.weights["A"] > targets.weights["B"]
    assert 0.0 <= targets.weights["B"] <= 1.0
    assert 0.0 <= targets.weights["A"] <= 1.0


def test_expected_shortfall_binary_trend_filter_scaling():
    rng = np.random.RandomState(42)
    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    ret_a = rng.normal(0.0005, 0.01, size=60)
    ret_b = rng.normal(0.0005, 0.01, size=60)
    prices_a = 10.0 * np.cumprod(1.0 + ret_a)
    prices_b = 10.0 * np.cumprod(1.0 + ret_b)
    # Ensure asset A is above SMA and asset B is below SMA
    prices_a[-1] = prices_a[-20:].mean() * 1.05
    prices_b[-1] = prices_b[-20:].mean() * 0.95
    df = pd.DataFrame({"A": prices_a, "B": prices_b}, index=dates)

    class MockDataStore:
        def get_price_frame(self, universe, date, use_nav=False):
            return df.copy()

    strategy = RiskParityExpectedShortfallFixedBudgetStrategy()
    context = StrategyContext(
        date=dates[-1],
        assets={},
        bars={},
        state=None,
        data=MockDataStore(),
        params={
            "rolling_window": 30,
            "min_periods": 20,
            "risk_budgets": {"A": 0.5, "B": 0.5},
            "trend_filter_window": 20,
            "trend_filter_mode": "binary",
            "trend_filter_scale_down": 0.25,
        },
    )

    targets = strategy._inverse_vol_target(context, ["A", "B"])
    assert targets is not None
    assert targets.weights["A"] > targets.weights["B"]


def test_expected_shortfall_aqr_multi_horizon_trend_filter():
    rng = np.random.RandomState(42)
    dates = pd.date_range("2023-01-01", periods=300, freq="B")
    
    # Asset A: stochastic upward trend (returns > 0 across 21d, 63d, 252d)
    ret_a = rng.normal(0.002, 0.01, size=300)
    prices_a = 10.0 * np.cumprod(1.0 + ret_a)
    
    # Asset B: stochastic down then strong rebound (positive over 21d & 63d, negative over 252d)
    ret_b = rng.normal(-0.002, 0.01, size=300)
    ret_b[-65:] = rng.normal(0.005, 0.01, size=65)
    prices_b = 20.0 * np.cumprod(1.0 + ret_b)
    
    # Asset C: stochastic downward trend (returns < 0 across all horizons)
    ret_c = rng.normal(-0.002, 0.01, size=300)
    prices_c = 20.0 * np.cumprod(1.0 + ret_c)

    # Force endpoint return checks explicitly
    assert prices_a[-1] > prices_a[-21] and prices_a[-1] > prices_a[-63] and prices_a[-1] > prices_a[-252]
    assert prices_b[-1] > prices_b[-21] and prices_b[-1] > prices_b[-63] and prices_b[-1] < prices_b[-252]
    assert prices_c[-1] < prices_c[-21] and prices_c[-1] < prices_c[-63] and prices_c[-1] < prices_c[-252]

    df = pd.DataFrame({"A": prices_a, "B": prices_b, "C": prices_c}, index=dates)

    class MockDataStore:
        def get_price_frame(self, universe, date, use_nav=False):
            return df.copy()

    strategy = RiskParityExpectedShortfallFixedBudgetStrategy()
    
    # Test 1: Standard AQR multi-horizon (windows=[21, 63, 252], signal="return", scale_down=0.0)
    context = StrategyContext(
        date=dates[-1],
        assets={},
        bars={},
        state=None,
        data=MockDataStore(),
        params={
            "rolling_window": 60,
            "min_periods": 30,
            "risk_budgets": {"A": 0.34, "B": 0.33, "C": 0.33},
            "trend_filter_mode": "aqr_multi_horizon",
            "trend_filter_windows": [21, 63, 252],
            "trend_filter_signal": "return",
            "trend_filter_scale_down": 0.0,
        },
    )

    targets = strategy._inverse_vol_target(context, ["A", "B", "C"])
    assert targets is not None
    # Score for A should be 1.0, B should be 2/3 (~0.667), C should be 0.0
    assert targets.weights["A"] > targets.weights["B"] > targets.weights["C"]
    assert targets.weights["C"] == pytest.approx(0.0)
    assert targets.weights["B"] > 0.0

    # Test 2: Multi-horizon with scale_down = 0.25 (C should retain base weight)
    context_scale = StrategyContext(
        date=dates[-1],
        assets={},
        bars={},
        state=None,
        data=MockDataStore(),
        params={
            "rolling_window": 60,
            "min_periods": 30,
            "risk_budgets": {"A": 0.34, "B": 0.33, "C": 0.33},
            "trend_filter_mode": "aqr_momentum",
            "trend_filter_windows": [21, 63, 252],
            "trend_filter_signal": "return",
            "trend_filter_scale_down": 0.25,
        },
    )
    targets_scale = strategy._inverse_vol_target(context_scale, ["A", "B", "C"])
    assert targets_scale is not None
    assert targets_scale.weights["C"] > 0.0

    # Test 3: Multi-horizon with signal="ma"
    context_ma = StrategyContext(
        date=dates[-1],
        assets={},
        bars={},
        state=None,
        data=MockDataStore(),
        params={
            "rolling_window": 60,
            "min_periods": 30,
            "risk_budgets": {"A": 0.34, "B": 0.33, "C": 0.33},
            "trend_filter_mode": "aqr",
            "trend_filter_windows": [20, 60, 120],
            "trend_filter_signal": "ma",
            "trend_filter_scale_down": 0.0,
        },
    )
    targets_ma = strategy._inverse_vol_target(context_ma, ["A", "B", "C"])
    assert targets_ma is not None
    assert targets_ma.weights["A"] > targets_ma.weights["C"]

