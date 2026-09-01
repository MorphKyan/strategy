# -*- coding: utf-8 -*-
"""Unit tests for Constrained and Regularized ES Risk Parity (Roncalli 2019)."""

import numpy as np
import pytest

from src.platform_core.strategies.expected_shortfall import (
    RiskParityExpectedShortfallFixedBudgetStrategy,
)


def test_constrained_es_solver_respects_bounds_and_sum_to_one():
    np.random.seed(42)
    t_obs, n_assets = 252, 6
    # Asset 2 (e.g. 30Y bond) has very low vol
    vols = np.array([0.18, 0.12, 0.05, 0.15, 0.16, 0.16]) / np.sqrt(252)
    corr = np.eye(n_assets) * 0.7 + 0.3
    cov = np.diag(vols) @ corr @ np.diag(vols)
    returns = np.random.multivariate_normal(np.zeros(n_assets), cov, size=t_obs)

    budgets = np.array([0.15, 0.15, 0.30, 0.15, 0.125, 0.125])
    confidence_level = 0.95

    # 1. Unconstrained
    w_unconstrained = RiskParityExpectedShortfallFixedBudgetStrategy._solve_expected_shortfall_risk_budget(
        returns, budgets, confidence_level
    )
    assert np.isclose(np.sum(w_unconstrained), 1.0)
    # Asset 2 should naturally take > 45%
    assert w_unconstrained[2] > 0.45

    # 2. Constrained: Asset 2 capped at 0.40
    max_weights = np.array([0.30, 0.30, 0.40, 0.30, 0.25, 0.25])
    min_weights = np.full(n_assets, 1e-4)

    w_constrained = RiskParityExpectedShortfallFixedBudgetStrategy._solve_constrained_expected_shortfall_risk_budget(
        returns,
        budgets,
        confidence_level,
        max_weights=max_weights,
        min_weights=min_weights,
        entropy_penalty=0.02,
    )

    assert np.isclose(np.sum(w_constrained), 1.0, atol=1e-5)
    assert np.all(w_constrained >= min_weights - 1e-6)
    assert np.all(w_constrained <= max_weights + 1e-6)
    # 30Y bond must be clamped right at the ceiling
    assert np.isclose(w_constrained[2], 0.40, atol=1e-3)
    # Remaining weights are strictly larger than unconstrained
    assert w_constrained[0] > w_unconstrained[0]
    assert w_constrained[1] > w_unconstrained[1]


def test_constrained_es_bisection_solver():
    np.random.seed(42)
    t_obs, n_assets = 252, 6
    vols = np.array([0.18, 0.12, 0.05, 0.15, 0.16, 0.16]) / np.sqrt(252)
    corr = np.eye(n_assets) * 0.7 + 0.3
    cov = np.diag(vols) @ corr @ np.diag(vols)
    returns = np.random.multivariate_normal(np.zeros(n_assets), cov, size=t_obs)

    budgets = np.array([0.15, 0.15, 0.30, 0.15, 0.125, 0.125])
    confidence_level = 0.95
    max_weights = np.array([0.30, 0.30, 0.40, 0.30, 0.25, 0.25])
    min_weights = np.full(n_assets, 1e-4)

    w_bisect = RiskParityExpectedShortfallFixedBudgetStrategy._solve_constrained_expected_shortfall_risk_budget(
        returns,
        budgets,
        confidence_level,
        max_weights=max_weights,
        min_weights=min_weights,
        entropy_penalty=0.0,
        solver_method="bisection",
    )

    assert np.isclose(np.sum(w_bisect), 1.0, atol=1e-4)
    assert np.all(w_bisect <= max_weights + 1e-3)
