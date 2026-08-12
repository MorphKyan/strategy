from __future__ import annotations

import numpy as np
import pytest

from src.platform_core.strategy import get_strategy_class
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
