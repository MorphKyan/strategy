"""Fixed-budget portfolio Expected Shortfall risk budgeting strategy."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import LinearConstraint, minimize

from src.platform_core.models import TargetPortfolio
from src.platform_core.strategy import RiskParityStrategy, StrategyContext


class RiskParityExpectedShortfallFixedBudgetStrategy(RiskParityStrategy):
    """Allocate portfolio Expected Shortfall to fixed, exogenous risk budgets."""

    name = "risk_parity_expected_shortfall_fixed_budget"
    version = "0.1.0"

    def _inverse_vol_target(
        self,
        context: StrategyContext,
        universe: list[str],
    ) -> TargetPortfolio | None:
        rolling_window = int(context.params.get("rolling_window", 120))
        min_periods = int(context.params.get("min_periods", rolling_window))
        confidence_level = float(context.params.get("confidence_level", 0.95))

        if rolling_window < 2 or min_periods < 2:
            raise ValueError("rolling_window and min_periods must both be at least 2.")
        if not 0.0 < confidence_level < 1.0:
            raise ValueError("confidence_level must be strictly between 0 and 1.")

        price_frame = context.data.get_price_frame(universe, context.date, use_nav=False)
        if price_frame is None or price_frame.empty:
            return None
        price_frame.index = pd.to_datetime(price_frame.index)
        if len(price_frame) < min_periods + 1:
            return None

        returns = price_frame.pct_change().dropna().tail(rolling_window)
        if len(returns) < min_periods:
            return None

        budgets = self._risk_budgets(context, universe)
        weights = self._solve_expected_shortfall_risk_budget(
            returns.to_numpy(dtype=float),
            budgets,
            confidence_level,
        )

        volatility_target = context.params.get("volatility_target")
        if volatility_target is not None:
            target = float(volatility_target)
            if target > 0.0:
                covariance = np.cov(returns.to_numpy(dtype=float), rowvar=False)
                covariance = np.atleast_2d(covariance)
                portfolio_volatility = float(
                    np.sqrt(max(weights @ covariance @ weights, 0.0) * 252.0)
                )
                if portfolio_volatility > 0.0:
                    weights *= min(1.0, target / portfolio_volatility)

        return TargetPortfolio(
            {asset_id: float(weights[index]) for index, asset_id in enumerate(universe)}
        )

    @staticmethod
    def _risk_budgets(context: StrategyContext, universe: list[str]) -> np.ndarray:
        configured = context.params.get("risk_budgets")
        if not isinstance(configured, dict):
            raise ValueError("risk_budgets must be a mapping keyed by every universe asset.")

        missing = [asset_id for asset_id in universe if asset_id not in configured]
        extra = [asset_id for asset_id in configured if asset_id not in universe]
        if missing or extra:
            raise ValueError(
                f"risk_budgets must match universe exactly; missing={missing}, extra={extra}."
            )

        budgets = np.asarray([float(configured[asset_id]) for asset_id in universe])
        if not np.all(np.isfinite(budgets)) or np.any(budgets <= 0.0):
            raise ValueError("Every risk budget must be finite and strictly positive.")
        return budgets / budgets.sum()

    @staticmethod
    def _solve_expected_shortfall_risk_budget(
        returns: np.ndarray,
        budgets: np.ndarray,
        confidence_level: float,
    ) -> np.ndarray:
        """Solve the convex Rockafellar-Uryasev ES risk-budgeting problem."""
        observations, assets = returns.shape
        if observations < 2 or assets < 1 or not np.all(np.isfinite(returns)):
            raise ValueError("Expected Shortfall requires a finite 2D return matrix.")
        if budgets.shape != (assets,):
            raise ValueError("Risk budget count must match the return matrix columns.")

        tail_probability = 1.0 - confidence_level
        barrier_scale = 0.01
        initial_weights = budgets.copy()
        initial_losses = -(returns @ initial_weights)
        initial_var = float(np.quantile(initial_losses, confidence_level))
        initial_excess = np.maximum(initial_losses - initial_var, 0.0)
        initial = np.concatenate(
            [initial_weights, np.asarray([initial_var]), initial_excess]
        )

        # u_t >= -r_t'x - zeta  <=>  r_t'x + zeta + u_t >= 0
        constraint_matrix = np.zeros((observations, assets + 1 + observations))
        constraint_matrix[:, :assets] = returns
        constraint_matrix[:, assets] = 1.0
        constraint_matrix[:, assets + 1 :] = np.eye(observations)
        constraints = LinearConstraint(constraint_matrix, 0.0, np.inf)

        def objective(values: np.ndarray) -> float:
            exposures = values[:assets]
            var_level = values[assets]
            excess = values[assets + 1 :]
            expected_shortfall = var_level + excess.sum() / (
                tail_probability * observations
            )
            return float(
                expected_shortfall
                - barrier_scale * np.dot(budgets, np.log(exposures))
            )

        def gradient(values: np.ndarray) -> np.ndarray:
            exposures = values[:assets]
            result = np.zeros_like(values)
            result[:assets] = -barrier_scale * budgets / exposures
            result[assets] = 1.0
            result[assets + 1 :] = 1.0 / (tail_probability * observations)
            return result

        bounds = (
            [(1e-10, None)] * assets
            + [(None, None)]
            + [(0.0, None)] * observations
        )
        solution = minimize(
            objective,
            initial,
            jac=gradient,
            method="SLSQP",
            bounds=bounds,
            constraints=[constraints],
            options={"ftol": 1e-12, "maxiter": 1000, "disp": False},
        )
        if not solution.success:
            raise RuntimeError(
                f"Expected Shortfall risk-budgeting solver failed: {solution.message}"
            )

        exposures = np.asarray(solution.x[:assets], dtype=float)
        total = float(exposures.sum())
        if not np.all(np.isfinite(exposures)) or np.any(exposures <= 0.0) or total <= 0.0:
            raise RuntimeError("Expected Shortfall solver returned invalid exposures.")
        return exposures / total
