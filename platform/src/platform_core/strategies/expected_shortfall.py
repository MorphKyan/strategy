"""Fixed-budget portfolio Expected Shortfall risk budgeting strategy."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.platform_core.models import TargetPortfolio
from src.platform_core.interest_rates import SignalInterestRate, monthly_fast_slow_signal
from src.platform_core.strategy import RiskParityStrategy, StrategyContext


class RiskParityExpectedShortfallFixedBudgetStrategy(RiskParityStrategy):
    """Allocate portfolio Expected Shortfall to fixed, exogenous risk budgets."""

    name = "risk_parity_expected_shortfall_fixed_budget"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        super().initialize(context)
        if context.params.get("solver_method", "slsqp") not in {"auto", "slsqp"}:
            raise ValueError("Only the SLSQP ES budget solver is supported; the bisection fallback was removed.")
        if str(context.params.get("trend_filter_mode", "binary")).lower() == "fast_slow":
            self._signal_interest_rate = SignalInterestRate(context.params.get("trend_filter_risk_free"))

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

        if not 2 <= min_periods <= rolling_window:
            raise ValueError("Require 2 <= min_periods <= rolling_window.")
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

        entropy_penalty = float(
            context.params.get(
                "entropy_penalty",
                context.params.get(
                    "hhi_penalty",
                    context.params.get("hhi_penalty_gamma", 0.0),
                ),
            )
        )

        if not np.isfinite(entropy_penalty) or entropy_penalty < 0:
            raise ValueError("Entropy penalty must be finite and nonnegative.")
        configured_universe = context.params.get("universe") or list(context.assets) or universe
        bounds = []
        for name, default in (("max_weights", 1.0), ("min_weights", 0.0)):
            configured = context.params.get(name)
            if configured is None:
                bounds.append(None)
                continue
            if isinstance(configured, dict):
                if set(configured) - set(configured_universe):
                    raise ValueError(f"{name} contains assets outside the configured universe.")
                values = np.asarray([configured.get(asset_id, default) for asset_id in configured_universe], dtype=float)
            elif isinstance(configured, (list, tuple, np.ndarray)):
                values = np.asarray(configured, dtype=float)
            else:
                raise ValueError(f"{name} must be a mapping or a universe-aligned vector.")
            if (values.shape != (len(configured_universe),) or not np.isfinite(values).all()
                    or (values < 0).any() or (values > 1).any()):
                raise ValueError(f"{name} must contain one finite value in [0, 1] per configured asset.")
            bounds.append(values[[configured_universe.index(asset_id) for asset_id in universe]])
        max_weights, min_weights = bounds

        if max_weights is not None or min_weights is not None or entropy_penalty > 0.0:
            weights = self._solve_constrained_expected_shortfall_risk_budget(
                scenarios,
                budgets,
                confidence_level,
                max_weights=max_weights,
                min_weights=min_weights,
                entropy_penalty=entropy_penalty,
            )
        else:
            weights = self._solve_expected_shortfall_risk_budget(
                scenarios,
                budgets,
                confidence_level,
            )

        volatility_target = context.params.get("volatility_target")
        if volatility_target is not None:
            target = float(volatility_target)
            if not np.isfinite(target) or target <= 0:
                raise ValueError("volatility_target must be finite and positive when specified.")
            covariance = np.cov(returns.to_numpy(dtype=float), rowvar=False)
            covariance = np.atleast_2d(covariance)
            portfolio_volatility = float(
                np.sqrt(max(weights @ covariance @ weights, 0.0) * 252.0)
            )
            if portfolio_volatility > 0.0:
                weights *= min(1.0, target / portfolio_volatility)

        trend_filter_window = context.params.get("trend_filter_window")
        trend_filter_windows = context.params.get("trend_filter_windows")
        trend_filter_mode = str(context.params.get("trend_filter_mode", "binary")).lower()

        if trend_filter_mode == "fast_slow":
            signal_assets = context.params.get("trend_filter_assets", universe)
            if not isinstance(signal_assets, list):
                raise ValueError("trend_filter_assets must be a list of configured asset IDs.")
            unknown = set(signal_assets) - set(configured_universe)
            if unknown:
                raise ValueError(f"trend_filter_assets outside universe: {sorted(unknown)}")
            for index, asset_id in enumerate(universe):
                if asset_id not in signal_assets:
                    continue
                signal = monthly_fast_slow_signal(
                    price_frame[asset_id], context.date, self._signal_interest_rate, context.data.calendar
                )
                # During the 13-month signal warmup, retain this sleeve in cash.
                weights[index] *= 0.0 if signal is None else {
                    "bull": 1.0, "correction": 0.75, "rebound": 0.5, "bear": 0.25
                }[signal[0]]
        elif trend_filter_mode in ("aqr_multi_horizon", "aqr_momentum", "aqr"):
            if trend_filter_windows is not None:
                windows = [int(w) for w in trend_filter_windows if int(w) > 1]
            elif trend_filter_window is not None:
                tf_window = int(trend_filter_window)
                windows = [21, 63, tf_window] if tf_window > 63 else [21, 63, 252]
            else:
                windows = [21, 63, 252]

            tf_signal = str(context.params.get("trend_filter_signal", "return")).lower()
            tf_scale_down = float(context.params.get("trend_filter_scale_down", 0.0))

            for index, asset_id in enumerate(universe):
                series = price_frame[asset_id].dropna()
                if len(series) == 0:
                    continue
                current_price = float(series.iloc[-1])
                signals = []
                for w in windows:
                    if len(series) >= w:
                        if tf_signal == "ma":
                            ma_val = float(series.tail(w).mean())
                            signals.append(1.0 if current_price >= ma_val else 0.0)
                        else:  # return (AQR TSMOM momentum)
                            past_price = float(series.iloc[-w])
                            signals.append(1.0 if current_price >= past_price else 0.0)
                    else:
                        if len(series) > 1:
                            if tf_signal == "ma":
                                ma_val = float(series.mean())
                                signals.append(1.0 if current_price >= ma_val else 0.0)
                            else:
                                past_price = float(series.iloc[0])
                                signals.append(1.0 if current_price >= past_price else 0.0)
                        else:
                            signals.append(1.0)
                if signals:
                    score = float(np.mean(signals))
                    mult = tf_scale_down + (1.0 - tf_scale_down) * score
                    weights[index] *= mult
        elif trend_filter_window is not None:
            tf_window = int(trend_filter_window)
            if tf_window > 1:
                tf_type = str(context.params.get("trend_filter_type", "sma")).lower()
                tf_scale_down = float(context.params.get("trend_filter_scale_down", 0.0))
                for index, asset_id in enumerate(universe):
                    series = price_frame[asset_id].dropna()
                    if len(series) >= tf_window:
                        current_price = float(series.iloc[-1])
                        if tf_type == "ema":
                            ma_val = float(series.ewm(span=tf_window, adjust=False).mean().iloc[-1])
                        else:  # sma
                            ma_val = float(series.tail(tf_window).mean())
                        
                        if trend_filter_mode == "continuous":
                            # Custom heuristic linear SMA deviation score scaling: mult = clip(0.5 + 0.25 * z, 0.0, 1.0)
                            rolling_std = float(series.tail(tf_window).std())
                            if rolling_std > 1e-8:
                                z = (current_price - ma_val) / rolling_std
                                mult = float(np.clip(0.5 + 0.25 * z, 0.0, 1.0))
                            else:
                                mult = 1.0 if current_price >= ma_val else 0.0
                            weights[index] *= mult
                        else:
                            if current_price < ma_val:
                                # Below trend moving average: cut weight to scale_down (default 0.0)
                                weights[index] *= tf_scale_down

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

        configured_universe = context.params.get("universe") or list(context.assets) or universe
        missing = [asset_id for asset_id in configured_universe if asset_id not in configured]
        extra = [asset_id for asset_id in configured if asset_id not in configured_universe]
        if missing or extra:
            raise ValueError(
                f"risk_budgets must match universe exactly; missing={missing}, extra={extra}."
            )

        return RiskParityStrategy._normalize_risk_budgets(configured, universe)

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
        if not np.all(np.isfinite(exposures)) or np.any(exposures <= 0.0) or not np.isfinite(total) or total <= 0.0:
            raise RuntimeError("Expected Shortfall solver returned invalid exposures.")
        return exposures / total

    @staticmethod
    def _solve_constrained_expected_shortfall_risk_budget(
        returns: np.ndarray,
        budgets: np.ndarray,
        confidence_level: float,
        max_weights: np.ndarray | None = None,
        min_weights: np.ndarray | None = None,
        entropy_penalty: float = 0.0,
    ) -> np.ndarray:
        """Minimize ES risk-contribution budget error with box bounds and HHI penalty."""
        observations, assets = returns.shape
        if observations < 2 or assets < 1 or not np.all(np.isfinite(returns)):
            raise ValueError("Expected Shortfall requires a finite 2D return matrix.")
        if budgets.shape != (assets,):
            raise ValueError("Risk budget count must match the return matrix columns.")
        scale = float(np.max(np.abs(returns)))
        if scale == 0:
            raise ValueError("Expected Shortfall requires nonzero return scenarios.")
        # 风险贡献占比与收益单位无关，先统一量级避免单位影响数值梯度。
        returns = returns / scale

        min_w = (
            np.full(assets, 1e-6, dtype=float)
            if min_weights is None
            else np.asarray(min_weights, dtype=float)
        )
        max_w = (
            np.ones(assets, dtype=float)
            if max_weights is None
            else np.asarray(max_weights, dtype=float)
        )

        if min_w.shape != (assets,) or max_w.shape != (assets,):
            raise ValueError("Weight bound count must match the return matrix columns.")
        if (not np.all(np.isfinite(min_w)) or not np.all(np.isfinite(max_w))
                or np.any(min_w < 0) or np.any(max_w > 1) or np.any(min_w > max_w)):
            raise ValueError("Weight bounds must be finite and satisfy 0 <= min <= max <= 1.")
        if not np.isfinite(entropy_penalty) or entropy_penalty < 0:
            raise ValueError("Entropy penalty must be finite and nonnegative.")

        # Check feasibility of box constraints sum(min_w) <= 1 <= sum(max_w)
        if float(np.sum(min_w)) > 1.0 + 1e-10:
            raise ValueError(f"Sum of min_weights ({np.sum(min_w)}) exceeds 1.0.")
        if float(np.sum(max_w)) < 1.0 - 1e-10:
            raise ValueError(f"Sum of max_weights ({np.sum(max_w)}) is less than 1.0.")

        # Initial point: projected budgets onto box constraint and normalized
        w0 = RiskParityExpectedShortfallFixedBudgetStrategy._project_box_simplex(budgets, min_w, max_w)

        bounds = [(float(min_w[i]), float(max_w[i])) for i in range(assets)]
        constraints = [{"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}]

        def objective(w: np.ndarray) -> tuple[float, np.ndarray]:
            es_val, es_grad = (
                RiskParityExpectedShortfallFixedBudgetStrategy._empirical_es_and_gradient(
                    returns, w, confidence_level
                )
            )
            if es_val <= 1e-12:
                return 1e6, np.zeros_like(w)
            # Normalized Euler risk contributions p_i = RC_i / ES(w)
            p = w * es_grad / es_val
            error = p - budgets
            tracking_loss = float(error @ error)
            hhi_loss = float(entropy_penalty * np.sum(w ** 2))
            # 尾部样本固定时 ES 为线性函数；显式梯度避免差分跨过尾部切换点。
            gradient = 2 * es_grad / es_val * (error - error @ p) + 2 * entropy_penalty * w
            return tracking_loss + hhi_loss, gradient

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Values in x were outside bounds during a minimize step",
                category=RuntimeWarning,
            )
            solution = minimize(
                objective,
                w0,
                jac=True,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"ftol": 1e-12, "maxiter": 1000, "disp": False},
            )

        if not solution.success:
            raise RuntimeError(f"Constrained Expected Shortfall solver failed: {solution.message}")
        weights = RiskParityExpectedShortfallFixedBudgetStrategy._project_box_simplex(solution.x, min_w, max_w)
        es, _ = RiskParityExpectedShortfallFixedBudgetStrategy._empirical_es_and_gradient(returns, weights, confidence_level)
        if es <= 1e-12:
            raise RuntimeError("Constrained Expected Shortfall requires a positive portfolio tail loss.")
        return weights

    @staticmethod
    def _project_box_simplex(values: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> np.ndarray:
        """求满足上下限且和为 1 的权重，避免归一化重新破坏边界。"""
        values = np.asarray(values, dtype=float)
        if values.shape != lower.shape or not np.all(np.isfinite(values)):
            raise RuntimeError("Constrained Expected Shortfall solver returned invalid exposures.")
        values = np.clip(values, lower, upper)
        left = float(np.min(values - upper))
        right = float(np.max(values - lower))
        for _ in range(60):
            shift = (left + right) / 2
            weights = np.clip(values - shift, lower, upper)
            if float(weights.sum()) > 1:
                left = shift
            else:
                right = shift
        weights = np.clip(values - (left + right) / 2, lower, upper)
        if abs(float(weights.sum()) - 1) > 1e-9:
            raise RuntimeError("Cannot project Expected Shortfall weights onto the requested bounds.")
        return weights

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
        if not 0 < confidence_level < 1:
            raise ValueError("confidence_level must be strictly between 0 and 1.")
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
