# -*- coding: utf-8 -*-
"""ES 风险贡献预算与盒状约束的回归测试。"""

import numpy as np
import pytest
from types import SimpleNamespace

from src.platform_core.strategies.expected_shortfall import (
    RiskParityExpectedShortfallFixedBudgetStrategy,
)


def test_box_projection_preserves_binding_lower_bounds():
    lower = np.array([0.4, 0.0, 0.0])
    upper = np.array([1.0, 0.5, 0.5])
    weights = RiskParityExpectedShortfallFixedBudgetStrategy._project_box_simplex(
        np.array([0.4, 0.5, 0.5]), lower, upper)
    assert np.isclose(weights.sum(), 1)
    assert np.all(weights >= lower - 1e-10)
    assert np.all(weights <= upper + 1e-10)


def test_failed_constrained_solver_does_not_fabricate_weights(monkeypatch):
    from src.platform_core.strategies import expected_shortfall

    monkeypatch.setattr(expected_shortfall, "minimize", lambda *args, **kwargs: SimpleNamespace(
        x=np.array([0.4, 0.5, 0.5]), success=False, message="forced failure"))
    with pytest.raises(RuntimeError, match="forced failure"):
        RiskParityExpectedShortfallFixedBudgetStrategy._solve_constrained_expected_shortfall_risk_budget(
            np.array([[-.01, -.02, -.03], [-.02, -.01, -.04]]), np.full(3, 1 / 3), .95)


def test_constrained_budget_loss_is_invariant_to_return_units():
    losses = np.array([.01, .02, .03])
    returns = np.tile(-losses, (100, 1))
    budgets = np.array([.5, .3, .2])
    solve = RiskParityExpectedShortfallFixedBudgetStrategy._solve_constrained_expected_shortfall_risk_budget
    weights = solve(returns, budgets, .95)
    scaled = solve(returns * .001, budgets, .95)
    expected = budgets / losses
    expected /= expected.sum()
    assert weights == pytest.approx(expected, abs=1e-5)
    assert scaled == pytest.approx(expected, abs=1e-5)


@pytest.mark.parametrize("scale", [.001, 1000])
def test_return_units_do_not_send_nonsmooth_solver_to_a_different_boundary(scale):
    returns = np.random.default_rng(12).normal(0, [.01, .02, .03], (100, 3))
    budgets = np.array([.5, .3, .2])
    solve = RiskParityExpectedShortfallFixedBudgetStrategy._solve_constrained_expected_shortfall_risk_budget
    weights = solve(returns, budgets, .95)
    scaled = solve(returns * scale, budgets, .95)
    assert scaled == pytest.approx(weights, abs=2e-3)
    es, gradient = RiskParityExpectedShortfallFixedBudgetStrategy._empirical_es_and_gradient(returns, weights, .95)
    assert np.sum((weights * gradient / es - budgets) ** 2) < .001


def test_zero_risk_scenarios_cannot_produce_fictitious_risk_budget_weights():
    with pytest.raises(ValueError, match="nonzero"):
        RiskParityExpectedShortfallFixedBudgetStrategy._solve_constrained_expected_shortfall_risk_budget(
            np.zeros((10, 2)), np.array([.5, .5]), .95)


def test_no_loss_scenarios_cannot_be_accepted_as_a_solved_risk_budget():
    with pytest.raises(RuntimeError, match="positive portfolio tail loss"):
        RiskParityExpectedShortfallFixedBudgetStrategy._solve_constrained_expected_shortfall_risk_budget(
            np.full((10, 2), .01), np.array([.5, .5]), .95)


def test_constrained_es_gradient_matches_local_loss_change(monkeypatch):
    from src.platform_core.strategies import expected_shortfall

    def check_gradient(objective, initial, **kwargs):
        assert kwargs["jac"] is True
        weights = np.array([.4, .35, .25])
        _, gradient = objective(weights)
        step = 1e-7
        differences = [
            (objective(weights + direction * step)[0] - objective(weights - direction * step)[0]) / (2 * step)
            for direction in np.eye(3)
        ]
        assert gradient == pytest.approx(differences, rel=1e-5, abs=1e-7)
        return SimpleNamespace(success=True, x=initial)

    monkeypatch.setattr(expected_shortfall, "minimize", check_gradient)
    RiskParityExpectedShortfallFixedBudgetStrategy._solve_constrained_expected_shortfall_risk_budget(
        np.random.default_rng(12).normal(0, [.01, .02, .03], (100, 3)), np.array([.5, .3, .2]), .95,
        entropy_penalty=.02)
@pytest.mark.parametrize("lower,upper", [
    ([.5, .1, .1], [.2, .7, .7]), ([0, 0], [1, 1, 1]),
    ([0, 0, 0], [float("nan"), 1, 1]), ([0, 0, 0], [2, 1, 1]),
])
def test_invalid_box_constraints_are_rejected_instead_of_repaired(lower, upper):
    with pytest.raises(ValueError):
        RiskParityExpectedShortfallFixedBudgetStrategy._solve_constrained_expected_shortfall_risk_budget(
            np.array([[-.01, -.02, -.03], [-.02, -.01, -.04]]), np.full(3, 1 / 3), .95,
            min_weights=np.array(lower), max_weights=np.array(upper))


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
