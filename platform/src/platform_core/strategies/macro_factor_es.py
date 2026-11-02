# -*- coding: utf-8 -*-
"""平滑 PCA 代理因子的经验 ES 风险分配，资产预算走廊采用软惩罚。"""

from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.platform_core.models import TargetPortfolio
from src.platform_core.strategy import RiskParityStrategy, StrategyContext
from src.platform_core.strategies.expected_shortfall import RiskParityExpectedShortfallFixedBudgetStrategy as ES

class RiskParityMacroFactorStrategy(RiskParityStrategy):
    """PCA 是价格代理因子，不将其解释成已识别的经济宏观因子。"""

    name = "risk_parity_macro_factor"
    version = "0.2.0"

    @staticmethod
    def _risk_contributions(returns, weights, betas, confidence_level):
        es, marginal = ES._empirical_es_and_gradient(returns, weights, confidence_level)
        asset = weights * marginal
        factor = (betas.T @ weights) * (np.linalg.pinv(betas.T).T @ marginal)
        return es, asset, factor, float(es - factor.sum())

    def _inverse_vol_target(
        self,
        context: StrategyContext,
        universe: list[str],
    ) -> TargetPortfolio | None:
        rolling_window = int(context.params.get("rolling_window", 252))
        min_periods = int(context.params.get("min_periods", 120))
        volatility_target = float(context.params.get("volatility_target", 0.08))
        lambda_beta = float(context.params.get("lambda_beta", 0.85))
        confidence_level = float(context.params.get("confidence_level", 0.95))
        if not 0 < confidence_level < 1:
            raise ValueError("confidence_level must be strictly between 0 and 1.")
        if rolling_window < 2 or not 2 <= min_periods <= rolling_window:
            raise ValueError("Require 2 <= min_periods <= rolling_window.")
        if not 0 <= lambda_beta <= 1 or not np.isfinite(volatility_target) or volatility_target <= 0:
            raise ValueError("Require 0 <= lambda_beta <= 1 and positive finite volatility_target.")

        raw_base_budgets = context.params.get("risk_budgets", {})

        price_frame = context.data.get_price_frame(universe, context.date, use_nav=False)
        if price_frame is None or price_frame.empty:
            return None
        price_frame.index = pd.to_datetime(price_frame.index)
        price_frame = price_frame.loc[price_frame.index <= pd.Timestamp(context.date), universe]
        if len(price_frame) < min_periods + 1:
            return None

        returns = price_frame.pct_change(fill_method=None).dropna().tail(rolling_window)
        if len(returns) < min_periods:
            return None

        n_assets = len(universe)
        asset_cols = list(universe)

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
        Cov_R = np.atleast_2d(np.cov(R, rowvar=False))
        n_factors = B_smooth.shape[1]
        target_factor_budgets = np.full(n_factors, 1.0 / n_factors)

        # 3. Soft asset-budget corridor [0.65 * base, 1.35 * base]
        b_min = b_base * 0.65
        b_max = b_base * 1.35

        # 4. Factor Risk Contribution Objective with Asset Bounding Penalty
        def factor_rc_loss(w):
            if w.sum() <= 0:
                return 1e6
            w = w / np.sum(w)

            es, trc_asset, trc_factor, residual = self._risk_contributions(R, w, B_smooth, confidence_level)
            if es <= 1e-12:
                return 1e6
            # 保留负贡献及未解释风险；取绝对值会把对冲贡献伪装成正风险。
            factor_budget_share = trc_factor / es

            # Penalty if asset risk budget violates corridor bounds [b_min, b_max]
            b_asset = trc_asset / es
            penalty = np.sum(np.maximum(0, b_min - b_asset)**2 + np.maximum(0, b_asset - b_max)**2) * 100.0

            return float(np.sum((factor_budget_share - target_factor_budgets) ** 2) + (residual / es) ** 2 + penalty)

        w0 = ES._solve_expected_shortfall_risk_budget(R, b_base, confidence_level)
        if n_assets == 1:
            w_raw = np.ones(1)
        else:
            def simplex(log_ratios):
                logits = np.append(log_ratios, 0.)
                values = np.exp(logits - logits.max())
                return values / values.sum()

            # 固定最后一维，去除归一化权重的冗余尺度；尾部切换不光滑，采用无导数求解。
            initial = np.log(w0[:-1] / w0[-1])
            res = minimize(lambda x: factor_rc_loss(simplex(x)), initial, method="Powell",
                           options={"maxiter": 1000, "ftol": 1e-7, "xtol": 1e-6})
            if not res.success or not np.isfinite(res.x).all():
                raise RuntimeError(f"Macro-factor solver failed: {res.message}; no substitute weights were produced.")
            w_raw = simplex(res.x)
        es, asset_rc, factor_rc, residual = self._risk_contributions(R, w_raw, B_smooth, confidence_level)
        if es <= 0 or not np.isfinite(es):
            raise RuntimeError("Macro-factor solver produced nonpositive Expected Shortfall.")

        # 5. Volatility Target Overlay
        port_vol = float(np.sqrt(w_raw.T @ Cov_R @ w_raw) * np.sqrt(252.0))
        scale = 1.0
        if port_vol > volatility_target and port_vol > 0:
            scale = volatility_target / port_vol
        scale = min(scale, 1.0)

        weights = {asset_cols[i]: float(w_raw[i] * scale) for i in range(n_assets)}
        context.runtime["macro_factor_betas"] = B_smooth.tolist()
        context.runtime["macro_factor_universe"] = asset_cols
        context.runtime["macro_factor_es"] = {"expected_shortfall": es,
            "asset_contributions": asset_rc.tolist(), "factor_contributions": factor_rc.tolist(),
            "residual_contribution": residual, "objective": factor_rc_loss(w_raw)}
        return TargetPortfolio(weights)
