# -*- coding: utf-8 -*-
"""平滑 PCA 暴露的协方差因子风险平价，资产预算区间采用软惩罚。"""

from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.platform_core.models import TargetPortfolio
from src.platform_core.strategy import RiskParityStrategy, StrategyContext

class RiskParityMacroFactorStrategy(RiskParityStrategy):
    """PCA 因子风险分配；没有执行 Expected Shortfall 优化。"""

    name = "risk_parity_macro_factor"
    version = "0.1.0"

    def _inverse_vol_target(
        self,
        context: StrategyContext,
        universe: list[str],
    ) -> TargetPortfolio | None:
        rolling_window = int(context.params.get("rolling_window", 252))
        min_periods = int(context.params.get("min_periods", 120))
        volatility_target = float(context.params.get("volatility_target", 0.08))
        lambda_beta = float(context.params.get("lambda_beta", 0.85))
        if rolling_window < 2 or not 2 <= min_periods <= rolling_window:
            raise ValueError("Require 2 <= min_periods <= rolling_window.")
        if not 0 <= lambda_beta <= 1 or not np.isfinite(volatility_target) or volatility_target <= 0:
            raise ValueError("Require 0 <= lambda_beta <= 1 and positive finite volatility_target.")

        raw_base_budgets = context.params.get("risk_budgets", {})

        price_frame = context.data.get_price_frame(universe, context.date, use_nav=False)
        if price_frame is None or price_frame.empty:
            return None
        price_frame.index = pd.to_datetime(price_frame.index)
        if len(price_frame) < min_periods + 1:
            return None

        returns = price_frame.pct_change().dropna().tail(rolling_window)
        if len(returns) < min_periods:
            return None

        n_assets = len(universe)
        asset_cols = [col for col in universe if col in returns.columns]
        if len(asset_cols) < n_assets:
            asset_cols = list(returns.columns)
            n_assets = len(asset_cols)

        # Base budgets
        b_base = self._normalize_risk_budgets(raw_base_budgets, asset_cols)

        R = returns[asset_cols].values # (T, N)

        # 1. SVD/PCA betas with EWMA smoothing
        _, _, Vt = np.linalg.svd(R - np.mean(R, axis=0), full_matrices=False)
        B_raw = Vt[:3, :].T

        previous = np.asarray(context.runtime.get("macro_factor_betas", []))
        if previous.shape != B_raw.shape or context.runtime.get("macro_factor_universe") != asset_cols:
            B_smooth = B_raw
        else:
            # PCA 轴的正负号等价，先对齐才能对跨期暴露求均值。
            B_raw = B_raw * np.where(np.sum(previous * B_raw, axis=0) < 0, -1.0, 1.0)
            B_smooth = lambda_beta * previous + (1.0 - lambda_beta) * B_raw

        # 2. Asset Covariance Matrix
        Cov_R = np.cov(R, rowvar=False) + np.eye(n_assets) * 1e-6
        n_factors = B_smooth.shape[1]
        target_factor_budgets = np.full(n_factors, 1.0 / n_factors)
        B_pinv = np.linalg.pinv(B_smooth.T)

        # 3. Soft asset-budget corridor [0.65 * base, 1.35 * base]
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
        if not res.success or not np.isfinite(res.x).all() or np.sum(res.x) <= 0:
            raise RuntimeError("Macro-factor solver failed; no substitute weights were produced.")
        w_raw = np.maximum(res.x, 0.0)
        w_raw = w_raw / np.sum(w_raw)

        # 5. Volatility Target Overlay
        port_vol = float(np.sqrt(w_raw.T @ Cov_R @ w_raw) * np.sqrt(252.0))
        scale = 1.0
        if port_vol > volatility_target and port_vol > 0:
            scale = volatility_target / port_vol
        scale = min(scale, 1.0)

        weights = {asset_cols[i]: float(w_raw[i] * scale) for i in range(n_assets)}
        context.runtime["macro_factor_betas"] = B_smooth.tolist()
        context.runtime["macro_factor_universe"] = asset_cols
        return TargetPortfolio(weights)
