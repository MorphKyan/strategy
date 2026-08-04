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
