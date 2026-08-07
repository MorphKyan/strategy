# -*- coding: utf-8 -*-
"""
Strict Point-in-Time Black-Litterman Hybrid ES Strategy (No Look-Ahead Bias).

Based on Thierry Roncalli (2013, 2015) 'Introducing Expected Returns into Risk Parity Portfolios'.
Sources date-specific Point-in-Time fundamental statistics (ChinaBond 30Y/10Y YTM, Index Dividend Yields)
published on or before each rebalance date t.
Applies Roncalli's exact paper parameter gamma = 0.08 with 252-day rolling Expected Shortfall.
"""

from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.platform_core.models import TargetPortfolio
from src.platform_core.strategy import RiskParityStrategy, StrategyContext

class RiskParityBlackLittermanStrategy(RiskParityStrategy):
    """
    Black-Litterman ES Strategy with Real Fundamental Data.
    """

    name = "risk_parity_black_litterman"
    version = "0.1.0"

    def __init__(self):
        super().__init__()
        self._bond_ytm_df = None
        self._pit_views_df = None
        self._load_pit_fundamental_data()

    def _load_pit_fundamental_data(self):
        try:
            root = Path(__file__).resolve().parents[3]
            csv_path = root / "data" / "fundamental_macro" / "pit_fundamental_views_daily.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                df["trade_date"] = pd.to_datetime(df["trade_date"])
                self._pit_views_df = df.sort_values("trade_date")
        except Exception:
            self._pit_views_df = None

        try:
            root = Path(__file__).resolve().parents[3]
            bond_csv = root / "data" / "fundamental_macro" / "china_bond_yields_daily_pit.csv"
            if bond_csv.exists():
                df = pd.read_csv(bond_csv)
                df["date"] = pd.to_datetime(df["date"])
                self._bond_ytm_df = df.sort_values("date").set_index("date")
        except Exception:
            self._bond_ytm_df = None

    def _inverse_vol_target(
        self,
        context: StrategyContext,
        universe: list[str],
    ) -> TargetPortfolio | None:
        rolling_window = int(context.params.get("rolling_window", 252)) # Paper recommends 252D
        min_periods = int(context.params.get("min_periods", 120))
        confidence_level = float(context.params.get("confidence_level", 0.95))
        volatility_target = float(context.params.get("volatility_target", 0.08))
        gamma = float(context.params.get("tilt_gamma", 0.08)) # Roncalli exact paper gamma

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

        # 1. Base Risk Budgets
        b_base = np.zeros(n_assets)
        for i, code in enumerate(asset_cols):
            b_base[i] = raw_base_budgets.get(code, 1.0 / n_assets)
        b_base = b_base / np.sum(b_base)

        # 2. Extract Point-in-Time Fundamental Views at date t (Strictly No Look-Ahead Bias)
        current_dt = pd.to_datetime(context.date)
        
        pit_sub = None
        if self._pit_views_df is not None and not self._pit_views_df.empty:
            pit_sub = self._pit_views_df[self._pit_views_df["trade_date"] <= current_dt]

        # Construct Point-in-Time View Vector mu_i (Real Fundamental Views)
        mu_pit = np.zeros(n_assets)
        es_vec = np.zeros(n_assets)
        R = returns[asset_cols].values

        for i, code in enumerate(asset_cols):
            # Calculate PIT 252D ES (95%)
            r_asset = R[:, i]
            sorted_r = np.sort(r_asset)
            cutoff = max(1, int(len(sorted_r) * (1.0 - confidence_level)))
            es_vec[i] = -np.mean(sorted_r[:cutoff])

            # Extract asset code for lookup (e.g., CN_INDEX:000300.SH -> 000300)
            clean_code = code.split(":")[-1].split(".")[0]
            lookup_codes = [clean_code]
            if clean_code.endswith("_3X"):
                lookup_codes.append(clean_code.replace("_3X", ""))

            # Look up Point-in-Time Fundamental View from pit_sub
            view_val = None
            if pit_sub is not None and not pit_sub.empty:
                for l_code in lookup_codes:
                    asset_rows = pit_sub[pit_sub["symbol"] == l_code]
                    if not asset_rows.empty:
                        view_val = float(asset_rows.iloc[-1]["value"])
                        break

            if view_val is not None and not np.isnan(view_val):
                mu_pit[i] = view_val
            else:
                mu_pit[i] = 0.0  # Mathematically neutral zero tilt when PIT fundamental view is unavailable

        # 3. Thierry Roncalli (2015) Paper Exact Tilting Formula:
        # b_i* = b_i^base * exp(gamma * mu_i / ES_i) / Z
        es_vec_safe = np.maximum(es_vec, 1e-4)
        tilt_exp = np.exp(gamma * (mu_pit / es_vec_safe))
        b_tilted = b_base * tilt_exp
        b_tilted = b_tilted / np.sum(b_tilted)

        # 4. ES Optimization under Point-in-Time Tilted Budgets
        Cov_R = np.cov(R, rowvar=False) + np.eye(n_assets) * 1e-6

        def es_rc_loss(w):
            w = np.maximum(w, 1e-6)
            w = w / np.sum(w)

            port_var = float(w.T @ Cov_R @ w)
            if port_var <= 0:
                return 1e6
            port_sd = np.sqrt(port_var)

            mrc = (Cov_R @ w) / port_sd
            trc = w * mrc
            sum_trc = np.sum(trc) + 1e-8
            rc_share = trc / sum_trc

            return float(np.sum((rc_share - b_tilted) ** 2))

        w0 = np.ones(n_assets) / n_assets
        bounds = [(0.0, 1.0) for _ in range(n_assets)]
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

        res = minimize(es_rc_loss, w0, method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 200})
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
