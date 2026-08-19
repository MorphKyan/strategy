"""Fixed-budget portfolio Expected Shortfall risk budgeting strategy."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.optimize import minimize

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
        es_method = str(context.params.get("es_method", "historical")).lower()
        fhs_decay = float(context.params.get("fhs_decay", 0.94))

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

        scenarios = self._expected_shortfall_scenarios(
            returns.to_numpy(dtype=float),
            method=es_method,
            fhs_decay=fhs_decay,
        )

        budgets = self._risk_budgets(context, universe)
        weights = self._solve_expected_shortfall_risk_budget(
            scenarios,
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
    def _expected_shortfall_scenarios(
        returns: np.ndarray,
        method: str = "historical",
        fhs_decay: float = 0.94,
    ) -> np.ndarray:
        """Build raw or volatility-filtered historical return scenarios.

        Filtered historical simulation standardizes each return by the EWMA
        volatility forecast available immediately before that observation and
        rescales the residuals by the latest one-step-ahead EWMA forecast. The
        same date is retained across assets, preserving cross-asset tail
        dependence in each historical scenario.
        """
        values = np.asarray(returns, dtype=float)
        if values.ndim != 2 or values.shape[0] < 2 or not np.all(np.isfinite(values)):
            raise ValueError("Expected Shortfall scenarios require a finite 2D return matrix.")
        if method == "historical":
            return values.copy()
        if method != "filtered":
            raise ValueError("es_method must be either 'historical' or 'filtered'.")
        if not 0.0 < fhs_decay < 1.0:
            raise ValueError("fhs_decay must be strictly between 0 and 1.")

        observations, assets = values.shape
        unconditional = np.var(values, axis=0, ddof=1)
        positive = unconditional[unconditional > 1e-16]
        fallback = float(np.median(positive)) if positive.size else 1e-8
        variance = np.where(unconditional > 1e-16, unconditional, fallback)
        forecasts = np.empty((observations, assets), dtype=float)
        for index in range(observations):
            forecasts[index] = np.sqrt(np.maximum(variance, 1e-16))
            variance = fhs_decay * variance + (1.0 - fhs_decay) * values[index] ** 2

        residuals = values / forecasts
        latest_volatility = np.sqrt(np.maximum(variance, 1e-16))
        scenarios = residuals * latest_volatility
        if not np.all(np.isfinite(scenarios)):
            raise ValueError("Filtered historical simulation produced invalid scenarios.")
        return scenarios

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

        barrier_scale = 0.01
        initial_weights = budgets.copy()

        def objective(values: np.ndarray) -> float:
            expected_shortfall, _ = (
                RiskParityExpectedShortfallFixedBudgetStrategy._empirical_es_and_gradient(
                    returns, values, confidence_level
                )
            )
            return float(
                expected_shortfall
                - barrier_scale * np.dot(budgets, np.log(values))
            )

        def gradient(values: np.ndarray) -> np.ndarray:
            _, es_gradient = (
                RiskParityExpectedShortfallFixedBudgetStrategy._empirical_es_and_gradient(
                    returns, values, confidence_level
                )
            )
            return es_gradient - barrier_scale * budgets / values

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Values in x were outside bounds during a minimize step",
                category=RuntimeWarning,
            )
            solution = minimize(
                objective,
                initial_weights,
                jac=gradient,
                method="SLSQP",
                bounds=[(1e-10, None)] * assets,
                options={"ftol": 1e-12, "maxiter": 1000, "disp": False},
            )
        if not solution.success:
            raise RuntimeError(
                f"Expected Shortfall risk-budgeting solver failed: {solution.message}"
            )

        exposures = np.asarray(solution.x, dtype=float)
        total = float(exposures.sum())
        if not np.all(np.isfinite(exposures)) or np.any(exposures <= 0.0) or total <= 0.0:
            raise RuntimeError("Expected Shortfall solver returned invalid exposures.")
        return exposures / total

    @staticmethod
    def _empirical_es_and_gradient(
        returns: np.ndarray,
        exposures: np.ndarray,
        confidence_level: float,
    ) -> tuple[float, np.ndarray]:
        """Return empirical ES and a tie-symmetric subgradient.

        Eliminating the Rockafellar-Uryasev auxiliary variables keeps the
        numerical problem at the number of assets instead of adding one
        variable per observation. Fractional tail mass handles confidence
        levels whose effective tail count is not an integer.
        """
        losses = -(returns @ exposures)
        tail_mass = (1.0 - confidence_level) * len(losses)
        if tail_mass <= 0.0:
            raise ValueError("Expected Shortfall tail mass must be positive.")
        order = np.argsort(-losses, kind="mergesort")
        coefficients = np.zeros(len(losses), dtype=float)
        full = min(int(np.floor(tail_mass)), len(losses))
        if full:
            coefficients[order[:full]] = 1.0
        fraction = tail_mass - full
        if fraction > 1e-14 and full < len(losses):
            coefficients[order[full]] = fraction

        # Average inclusion mass across observations tied at the boundary so
        # row ordering cannot determine the risk-budget solution.
        included = np.flatnonzero(coefficients > 0.0)
        if included.size:
            boundary_loss = losses[included].min()
            tied = np.flatnonzero(np.isclose(losses, boundary_loss, rtol=1e-12, atol=1e-15))
            tied_mass = coefficients[tied].sum()
            if len(tied) > 1 and tied_mass > 0.0:
                coefficients[tied] = tied_mass / len(tied)

        value = float(np.dot(coefficients, losses) / tail_mass)
        gradient = -(coefficients @ returns) / tail_mass
        return value, np.asarray(gradient, dtype=float)
