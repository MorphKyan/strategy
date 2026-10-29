# -*- coding: utf-8 -*-
"""PIT 基本面按 ES 缩放预算，再以协方差风险平价分配权重。

注册名沿用旧配置；当前实现没有 Black-Litterman 贝叶斯后验。
"""

from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.platform_core.models import TargetPortfolio
from src.platform_core.strategy import RiskParityStrategy, StrategyContext

class RiskParityBlackLittermanStrategy(RiskParityStrategy):
    """基本面倾斜预算的协方差风险平价。"""

    name = "risk_parity_black_litterman"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        super().initialize(context)
        self._pit_views_df = None
        csv_path = Path(context.data.data_dir) / "fundamental_macro" / "pit_fundamental_views_daily.csv"
        if csv_path.exists():
            frame = pd.read_csv(csv_path, dtype={"symbol": str}, usecols=["trade_date", "symbol", "value"])
            frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="raise")
            frame["symbol"] = frame["symbol"].str.strip()
            frame["value"] = pd.to_numeric(frame["value"], errors="raise")
            if (frame[["trade_date", "symbol"]].isna().any().any()
                    or frame["symbol"].str.strip().eq("").any()
                    or not np.isfinite(frame["value"]).all()
                    or frame.duplicated(["trade_date", "symbol"]).any()):
                raise ValueError(f"Invalid or duplicate PIT fundamental observations: {csv_path}")
            self._pit_views_df = frame.sort_values("trade_date")

    def _inverse_vol_target(
        self,
        context: StrategyContext,
        universe: list[str],
    ) -> TargetPortfolio | None:
        rolling_window = int(context.params.get("rolling_window", 252))
        min_periods = int(context.params.get("min_periods", 120))
        confidence_level = float(context.params.get("confidence_level", 0.95))
        volatility_target = float(context.params.get("volatility_target", 0.08))
        gamma = float(context.params.get("tilt_gamma", 0.08))
        if rolling_window < 2 or not 2 <= min_periods <= rolling_window:
            raise ValueError("Require 2 <= min_periods <= rolling_window.")
        if not 0 < confidence_level < 1 or not np.isfinite([volatility_target, gamma]).all() or volatility_target <= 0:
            raise ValueError("Require valid confidence_level, positive volatility_target and finite tilt_gamma.")

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

        # 1. Base Risk Budgets
        b_base = self._normalize_risk_budgets(raw_base_budgets, asset_cols)

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

        # 在对数域归一化，避免较大的有效倾斜值使 exp 溢出。
        es_vec_safe = np.maximum(es_vec, 1e-4)
        log_budgets = np.log(b_base) + gamma * (mu_pit / es_vec_safe)
        if not np.isfinite(log_budgets).all():
            raise ValueError("Fundamental budget tilt is not finite.")
        b_tilted = np.exp(log_budgets - log_budgets.max())
        b_tilted /= b_tilted.sum()

        # 4. Covariance risk parity under the tilted budgets
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
        if not res.success or not np.isfinite(res.x).all() or np.sum(res.x) <= 0:
            raise RuntimeError("Fundamental risk-budget solver failed; no substitute weights were produced.")
        w_raw = np.maximum(res.x, 0.0)
        w_raw = w_raw / np.sum(w_raw)

        # 5. Volatility Target Overlay
        port_vol = float(np.sqrt(w_raw.T @ Cov_R @ w_raw) * np.sqrt(252.0))
        scale = 1.0
        if port_vol > volatility_target and port_vol > 0:
            scale = volatility_target / port_vol
        scale = min(scale, 1.0)

        weights = {asset_cols[i]: float(w_raw[i] * scale) for i in range(n_assets)}
        return TargetPortfolio(weights)
