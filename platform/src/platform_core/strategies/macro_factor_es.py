# -*- coding: utf-8 -*-
"""
Macro Factor ES Strategy (No Look-Ahead Bias).

Based on Thierry Roncalli & Guillaume Weisang (2016) 'Risk Parity Portfolios with Risk Factors'.
Implements Section 4 Constrained Risk Budgeting and Smooth Factor Parity:
1. 252-day SVD/PCA orthogonal factor decomposition;
2. EWMA Beta smoothing (lambda = 0.85);
3. Asset-level risk budget corridor bounds ([0.65 * base, 1.35 * base]).
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.platform_core.models import TargetPortfolio
from src.platform_core.strategy import RiskParityStrategy, StrategyContext

class RiskParityMacroFactorStrategy(RiskParityStrategy):
    """
    Macro Factor ES Strategy under Roncalli (2016) Sec 4 Standards.
    """

    name = "risk_parity_macro_factor"
    version = "0.1.0"

    def __init__(self):
        super().__init__()
        self._prev_B_smooth = None

    def _inverse_vol_target(
        self,
        context: StrategyContext,
        universe: list[str],
    ) -> TargetPortfolio | None:
        rolling_window = int(context.params.get("rolling_window", 252)) # Paper recommends 252D (1 year)
        min_periods = int(context.params.get("min_periods", 120))
        volatility_target = float(context.params.get("volatility_target", 0.08))
        lambda_beta = float(context.params.get("lambda_beta", 0.85)) # Roncalli 2016 Sec 4 EWMA Beta smoothing

        raw_base_budgets = context.params.get("risk_budgets", {})

        price_frame = context.data.get_price_frame(universe, context.date, use_nav=False)
        if price_frame is None or price_frame.empty:
            return None
        price_frame.index = pd.to_datetime(price_frame.index)
        if len(price_frame) < min_periods + 1:
            return None

        returns = price_frame.pct_change().dropna().tail(rolling_window)
        if len(returns) < min_periods - 5:
            return None

        n_assets = len(universe)
        asset_cols = [col for col in universe if col in returns.columns]
        if len(asset_cols) < n_assets:
            asset_cols = list(returns.columns)
            n_assets = len(asset_cols)

        # Base budgets
        b_base = np.zeros(n_assets)
        for i, code in enumerate(asset_cols):
            b_base[i] = raw_base_budgets.get(code, 1.0 / n_assets)
        b_base = b_base / np.sum(b_base)

        R = returns[asset_cols].values # (T, N)
        T = len(returns)

        # 1. Roncalli & Weisang (2016) SVD/PCA Betas + Section 4 EWMA Beta Smoothing
        try:
            U, S, Vt = np.linalg.svd(R - np.mean(R, axis=0), full_matrices=False)
            B_raw = Vt[:3, :].T # (N, 3) Factor Betas Matrix
        except Exception:
            B_raw = np.ones((n_assets, 3)) / 3.0

        if self._prev_B_smooth is None or self._prev_B_smooth.shape != B_raw.shape:
            B_smooth = B_raw
        else:
            B_smooth = lambda_beta * self._prev_B_smooth + (1.0 - lambda_beta) * B_raw
        self._prev_B_smooth = B_smooth

        # 2. Asset Covariance Matrix
        Cov_R = np.cov(R, rowvar=False) + np.eye(n_assets) * 1e-6
        target_factor_budgets = np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0])

        # 3. Section 4 Constrained Asset Budget Bounds [0.65 * base, 1.35 * base]
        b_min = b_base * 0.65
        b_max = b_base * 1.35

        # 4. Factor Risk Contribution Objective with Asset Bounding Penalty
        def factor_rc_loss(w):
            w = np.maximum(w, 1e-6)
            w = w / np.sum(w)

            port_var = float(w.T @ Cov_R @ w)
            if port_var <= 0:
                return 1e6
            port_sd = np.sqrt(port_var)

            mrc_asset = (Cov_R @ w) / port_sd
            factor_exp = B_smooth.T @ w # (3,)
            
            B_pinv = np.linalg.pinv(B_smooth.T)
            mrc_factor = B_pinv.T @ mrc_asset

            trc_factor = factor_exp * mrc_factor
            sum_trc = np.sum(np.abs(trc_factor)) + 1e-8
            factor_budget_share = np.abs(trc_factor) / sum_trc

            # Penalty if asset risk budget violates corridor bounds [b_min, b_max]
            trc_asset = w * mrc_asset
            b_asset = trc_asset / np.sum(trc_asset)
            penalty = np.sum(np.maximum(0, b_min - b_asset)**2 + np.maximum(0, b_asset - b_max)**2) * 100.0

            return float(np.sum((factor_budget_share - target_factor_budgets) ** 2) + penalty)

        w0 = np.ones(n_assets) / n_assets
        bounds = [(0.0, 1.0) for _ in range(n_assets)]
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

        res = minimize(factor_rc_loss, w0, method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 200})
        w_raw = np.maximum(res.x if res.success else w0, 0.0)
        w_raw = w_raw / np.sum(w_raw)

        # 5. Volatility Target Overlay
        port_vol = float(np.sqrt(w_raw.T @ Cov_R @ w_raw) * np.sqrt(252.0))
        scale = 1.0
        if port_vol > volatility_target and port_vol > 0:
            scale = volatility_target / port_vol
        scale = min(scale, 1.0)

        weights = {asset_cols[i]: float(w_raw[i] * scale) for i in range(n_assets)}
        return TargetPortfolio(weights)
