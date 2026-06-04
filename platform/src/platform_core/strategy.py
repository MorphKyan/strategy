from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import PointInTimeFundamentals
from src.platform_core.models import Asset, Bar, PortfolioState, TargetPortfolio


@dataclass
class StrategyContext:
    date: Any
    assets: dict[str, Asset]
    bars: dict[str, Bar]
    state: PortfolioState
    data: LocalCsvBarData
    params: dict[str, Any]
    runtime: dict[str, Any] = field(default_factory=dict)
    fundamental_provider: PointInTimeFundamentals | None = None

    def set_cooldown(self, days: int) -> None:
        self.runtime["cooldown_days"] = max(0, int(days))

    def set_rebalance_frequency(self, frequency: str) -> None:
        self.runtime["rebalance_frequency"] = frequency

    def tradable_asset_ids(self) -> list[str]:
        return [asset_id for asset_id in self.assets if asset_id in self.bars]

    def available_asset_ids(self) -> list[str]:
        return [
            asset_id
            for asset_id in self.tradable_asset_ids()
            if asset_id not in self.state.cooldown_pool
        ]

    def is_month_end(self) -> bool:
        return self.data.is_month_end(self.date)

    def fundamentals(self, asset_id: str) -> dict[str, float]:
        if self.fundamental_provider is None:
            return {}
        return self.fundamental_provider.get(asset_id, self.date)

    def filter_by_fundamentals(self, asset_ids: list[str], rules: dict[str, Any]) -> list[str]:
        if self.fundamental_provider is None:
            return []
        return self.fundamental_provider.filter(asset_ids, self.date, rules)


class Strategy:
    name = "base"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        return None

    def generate_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        raise NotImplementedError


class MonthlyEqualWeightStrategy(Strategy):
    name = "monthly_equal_weight"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        context.set_cooldown(int(context.params.get("cooldown_days", 0)))
        context.set_rebalance_frequency("monthly")

    def generate_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        if not context.params.get("rebalance_on_start", True) and context.state.last_date is None:
            return None
        if context.state.last_date is not None and not context.is_month_end():
            return None

        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets and asset_id not in context.state.cooldown_pool]
        return TargetPortfolio.equal_weight(universe)


class FundamentalValueEqualWeightStrategy(Strategy):
    name = "fundamental_value_equal_weight"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        context.set_cooldown(int(context.params.get("cooldown_days", 0)))
        context.set_rebalance_frequency(context.params.get("rebalance_frequency", "monthly"))

    def generate_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        frequency = context.runtime.get("rebalance_frequency", "monthly")
        if context.state.last_date is not None and frequency == "monthly" and not context.is_month_end():
            return None

        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets and asset_id not in context.state.cooldown_pool]
        rules = context.params.get("fundamental_rules", {})
        if rules:
            universe = context.filter_by_fundamentals(universe, rules)
        return TargetPortfolio.equal_weight(universe)



class DriftRebalanceFixedWeightStrategy(Strategy):
    name = "balanced"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        context.set_cooldown(int(context.params.get("cooldown_days", 0)))
        context.runtime["initial_weights"] = context.params.get("initial_weights", [])
        context.runtime["rebalance_threshold"] = float(context.params.get("rebalance_threshold", 0.05))

    def generate_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets and asset_id not in context.state.cooldown_pool]
        if not universe:
            return None

        initial_weights = context.runtime.get("initial_weights", [])
        if not initial_weights or len(initial_weights) != len(universe):
            initial_weights = [1.0 / len(universe)] * len(universe)
            context.runtime["initial_weights"] = initial_weights

        target_weights = {asset_id: float(w) for asset_id, w in zip(universe, initial_weights)}

        if context.state.last_date is None:
            return TargetPortfolio(target_weights)

        prices = {asset_id: bar.close for asset_id, bar in context.bars.items()}
        current_weights = context.state.weights(prices)

        threshold = context.runtime.get("rebalance_threshold", 0.05)
        for asset_id, target_w in target_weights.items():
            if abs(current_weights.get(asset_id, 0.0) - target_w) > threshold:
                return TargetPortfolio(target_weights)
        return None


class RiskParityStrategy(Strategy):
    name = "risk_parity"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        context.runtime["opened"] = context.params.get("init_mode", "calculate") == "manual"
        context.runtime["rebalance_frequency"] = context.params.get("rebalance_frequency", "quarterly")

    def generate_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets and asset_id not in context.state.cooldown_pool]
        if not universe:
            return None

        if not bool(context.runtime.get("opened", False)):
            target = self._initial_target(context, universe)
            if target is None:
                return None
            context.runtime["opened"] = True
            return target

        if not self._is_rebalance_day(context):
            return None

        target = self._inverse_vol_target(context, universe)
        if target is None:
            return None

        prices = {asset_id: bar.close for asset_id, bar in context.bars.items()}
        current_weights = context.state.weights(prices)
        threshold = float(context.params.get("rebalance_threshold", 0.05))
        for asset_id, target_weight in target.weights.items():
            if abs(current_weights.get(asset_id, 0.0) - target_weight) > threshold:
                return target
        return None

    def _initial_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        init_mode = context.params.get("init_mode", "calculate")
        if init_mode == "manual":
            weights = context.params.get("initial_weights", [])
            if len(weights) != len(universe):
                raise ValueError("initial_weights length must match risk parity universe length.")
            return TargetPortfolio({asset_id: float(weight) for asset_id, weight in zip(universe, weights)})

        init_calc_days = int(context.params.get("init_calc_days", 30))
        if self._calendar_index(context) < init_calc_days:
            return None
        return self._inverse_vol_target(context, universe)

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        rolling_window = int(context.params.get("rolling_window", context.params.get("ewma_span", 120)))
        min_periods = int(context.params.get("min_periods", context.params.get("ewma_min_periods", 20)))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        
        closes = {}
        for asset_id in universe:
            frame = context.data.frames.get(asset_id)
            if frame is None:
                return None
            col = "acc_nav" if (use_nav and "acc_nav" in frame.columns) else "close"
            history = frame[frame.index <= context.date][col]
            closes[asset_id] = history

        price_frame = pd.DataFrame(closes).dropna()
        if price_frame.empty:
            return None
            
        # Convert index to DatetimeIndex for resampling
        price_frame.index = pd.to_datetime(price_frame.index)
        
        if estimation_freq == "weekly":
            price_frame = price_frame.resample("W").last().dropna()
            window = max(2, int(rolling_window / 5))
            min_p = max(2, int(min_periods / 5))
        elif estimation_freq == "monthly":
            try:
                price_frame = price_frame.resample("ME").last().dropna()
            except Exception:
                price_frame = price_frame.resample("M").last().dropna()
            window = max(2, int(rolling_window / 20))
            min_p = max(2, int(min_periods / 20))
        else:
            window = rolling_window
            min_p = min_periods

        if len(price_frame) < min_p + 1:
            return None
        volatility = price_frame.pct_change().dropna().tail(window).std()
        volatility = volatility[volatility > 0]
        if len(volatility) != len(universe):
            return None
        inv_vol = 1.0 / volatility
        weights = inv_vol / inv_vol.sum()
        return TargetPortfolio({asset_id: float(weights[asset_id]) for asset_id in universe})

    @staticmethod
    def _calendar_index(context: StrategyContext) -> int:
        try:
            return context.data.calendar.index(context.date)
        except ValueError:
            return -1

    @staticmethod
    def _is_rebalance_day(context: StrategyContext) -> bool:
        idx = RiskParityStrategy._calendar_index(context)
        if idx < 0:
            return False
        if idx == len(context.data.calendar) - 1:
            return True
        current = context.date
        next_date = context.data.calendar[idx + 1]
        
        freq = context.runtime.get("rebalance_frequency", "quarterly")
        if freq == "semiannually":
            # Rebalance at the end of Q1 (March) and Q3 (September) to align with research "2QE" resampling
            current_q = (current.month - 1) // 3
            next_q = (next_date.month - 1) // 3
            return current_q != next_q and current_q in (0, 2)
        elif freq == "monthly":
            return current.year != next_date.year or current.month != next_date.month
        else: # quarterly
            current_quarter = (current.month - 1) // 3
            next_quarter = (next_date.month - 1) // 3
            return current.year != next_date.year or current_quarter != next_quarter


class RiskParityEWMAStrategy(RiskParityStrategy):
    name = "risk_parity_ewma"
    version = "0.1.0"

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        ewma_span = int(context.params.get("ewma_span", 60))
        ewma_min_periods = int(context.params.get("ewma_min_periods", 20))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        
        closes = {}
        for asset_id in universe:
            frame = context.data.frames.get(asset_id)
            if frame is None:
                return None
            col = "acc_nav" if (use_nav and "acc_nav" in frame.columns) else "close"
            history = frame[frame.index <= context.date][col]
            closes[asset_id] = history

        price_frame = pd.DataFrame(closes).dropna()
        if price_frame.empty:
            return None
            
        # Convert index to DatetimeIndex for resampling
        price_frame.index = pd.to_datetime(price_frame.index)
        
        if estimation_freq == "weekly":
            price_frame = price_frame.resample("W").last().dropna()
            span = max(2, int(ewma_span / 5))
            min_p = max(2, int(ewma_min_periods / 5))
        elif estimation_freq == "monthly":
            try:
                price_frame = price_frame.resample("ME").last().dropna()
            except Exception:
                price_frame = price_frame.resample("M").last().dropna()
            span = max(2, int(ewma_span / 20))
            min_p = max(2, int(ewma_min_periods / 20))
        else:
            span = ewma_span
            min_p = ewma_min_periods

        if len(price_frame) < min_p + 1:
            return None
        returns = price_frame.pct_change()
        volatility = returns.ewm(span=span, min_periods=min_p, adjust=False).std().iloc[-1]
        volatility = volatility[volatility > 0]
        if len(volatility) != len(universe):
            return None
        inv_vol = 1.0 / volatility
        weights = inv_vol / inv_vol.sum()
        return TargetPortfolio({asset_id: float(weights[asset_id]) for asset_id in universe})


class RiskParityEWMADrawdownRecoveryStrategy(RiskParityEWMAStrategy):
    name = "risk_parity_ewma_dd_recovery"
    version = "0.1.0"

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        ewma_span = int(context.params.get("ewma_span", 60))
        ewma_min_periods = int(context.params.get("ewma_min_periods", 20))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        
        alpha = float(context.params.get("dd_penalty_alpha", 1.0))
        beta = float(context.params.get("dd_recovery_beta", 2.0))
        dd_window = int(context.params.get("dd_window", 30))
        
        # Nonlinear Threshold parameter
        penalty_threshold = float(context.params.get("dd_penalty_threshold", 0.025))

        closes = {}
        for asset_id in universe:
            frame = context.data.frames.get(asset_id)
            if frame is None:
                return None
            col = "acc_nav" if (use_nav and "acc_nav" in frame.columns) else "close"
            history = frame[frame.index <= context.date][col]
            closes[asset_id] = history

        price_frame = pd.DataFrame(closes).dropna()
        if price_frame.empty:
            return None
            
        # Convert index to DatetimeIndex for resampling
        price_frame.index = pd.to_datetime(price_frame.index)
        
        if estimation_freq == "weekly":
            price_frame = price_frame.resample("W").last().dropna()
            span = max(2, int(ewma_span / 5))
            min_p = max(2, int(ewma_min_periods / 5))
        elif estimation_freq == "monthly":
            try:
                price_frame = price_frame.resample("ME").last().dropna()
            except Exception:
                price_frame = price_frame.resample("M").last().dropna()
            span = max(2, int(ewma_span / 20))
            min_p = max(2, int(ewma_min_periods / 20))
        else:
            span = ewma_span
            min_p = ewma_min_periods

        if len(price_frame) < min_p + 1:
            return None
        returns = price_frame.pct_change()
        volatility = returns.ewm(span=span, min_periods=min_p, adjust=False).std().iloc[-1]
        volatility = volatility[volatility > 0]
        if len(volatility) != len(universe):
            return None
            
        # Calculate adjustments for each asset
        adjusted_vol = {}
        for asset_id in universe:
            hist = price_frame[asset_id]
            if len(hist) < 2:
                adjusted_vol[asset_id] = volatility[asset_id]
                continue
                
            curr_price = hist.iloc[-1]
            cum_max = hist.cummax().iloc[-1]
            current_dd = curr_price / cum_max - 1.0 if cum_max > 0 else 0.0
            
            hist_slice = hist.tail(dd_window)
            if len(hist_slice) > 0:
                cum_max_slice = hist_slice.cummax()
                dd_series = hist_slice / cum_max_slice - 1.0
                min_dd = dd_series.min()
            else:
                min_dd = current_dd
                
            # Apply nonlinear threshold on penalty
            # Only apply penalty if the absolute drawdown exceeds penalty_threshold
            dd_abs = abs(current_dd)
            if penalty_threshold > 0:
                # Step function activation
                penalty_term = alpha * dd_abs if dd_abs >= penalty_threshold else 0.0
            else:
                penalty_term = alpha * dd_abs
                
            # Calculate recovery term directly without trend filtering
            recovery = max(0.0, current_dd - min_dd)
            recovery_term = beta * recovery
                
            factor = 1.0 + penalty_term - recovery_term
            factor = max(0.1, factor)
            
            adjusted_vol[asset_id] = volatility[asset_id] * factor

        # Recalculate weights based on adjusted volatility
        inv_vol = {}
        for asset_id in universe:
            v = adjusted_vol[asset_id]
            inv_vol[asset_id] = 1.0 / v if v > 0 else 0.0
            
        sum_inv = sum(inv_vol.values())
        if sum_inv == 0:
            return None
            
        weights = {asset_id: val / sum_inv for asset_id, val in inv_vol.items()}
        return TargetPortfolio({asset_id: float(weights[asset_id]) for asset_id in universe})


class RiskParityLWCovStrategy(RiskParityStrategy):
    """
    基于 Ledoit-Wolf 协方差收缩的风险平价策略 (RiskParityLWCovStrategy)
    
    相比于仅基于逆波动率的传统风险平价，本策略引入了资产之间的相关性。
    使用 Ledoit-Wolf 收缩估计协方差矩阵，结合了样本协方差矩阵与常数相关系数目标矩阵，
    从而在保证协方差矩阵正定性的同时平滑了历史噪声。
    使用 Cyclical Coordinate Descent (CCD) 算法对风险平价权重进行精确求解。
    """
    name = "risk_parity_lw_cov"
    version = "0.1.0"

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        import numpy as np  # 确保导入 numpy
        
        rolling_window = int(context.params.get("rolling_window", context.params.get("ewma_span", 120)))
        min_periods = int(context.params.get("min_periods", context.params.get("ewma_min_periods", 20)))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        shrinkage_target = context.params.get("shrinkage_target", "constant_correlation")
        
        closes = {}
        for asset_id in universe:
            frame = context.data.frames.get(asset_id)
            if frame is None:
                return None
            col = "acc_nav" if (use_nav and "acc_nav" in frame.columns) else "close"
            history = frame[frame.index <= context.date][col]
            closes[asset_id] = history

        price_frame = pd.DataFrame(closes).dropna()
        if price_frame.empty:
            return None
            
        # 转换为 DatetimeIndex
        price_frame.index = pd.to_datetime(price_frame.index)
        
        # 处理不同的估计频率
        if estimation_freq == "weekly":
            price_frame = price_frame.resample("W").last().dropna()
            window = max(2, int(rolling_window / 5))
            min_p = max(2, int(min_periods / 5))
        elif estimation_freq == "monthly":
            try:
                price_frame = price_frame.resample("ME").last().dropna()
            except Exception:
                price_frame = price_frame.resample("M").last().dropna()
            window = max(2, int(rolling_window / 20))
            min_p = max(2, int(min_periods / 20))
        else:
            window = rolling_window
            min_p = min_periods

        if len(price_frame) < min_p + 1:
            return None
            
        # 计算收益率
        returns = price_frame.pct_change().dropna().tail(window)
        if len(returns) < min_p:
            return None
            
        # 提取收益率 numpy 数组，大小为 (T, N)
        X = returns.values
        T, N = X.shape
        if N == 0:
            return None
            
        # 估算协方差矩阵 (Ledoit-Wolf 收缩)
        Sigma = self._estimate_covariance(X, shrinkage_target)
        
        # 求解风险平价权重
        try:
            weights = self._solve_risk_parity(Sigma)
        except Exception as e:
            # 如果求解失败，降级为等权重
            weights = np.ones(N) / N
            
        # 返回目标资产组合
        return TargetPortfolio({asset_id: float(weights[i]) for i, asset_id in enumerate(universe)})

    def _estimate_covariance(self, X: np.ndarray, target: str) -> np.ndarray:
        import numpy as np
        T, N = X.shape
        if N <= 1:
            return np.cov(X, rowvar=False).reshape(N, N)
            
        # 去均值
        X_demeaned = X - X.mean(axis=0)
        
        # 计算样本协方差
        S = np.dot(X_demeaned.T, X_demeaned) / T
        
        if target == "constant_correlation":
            # 提取对角方差和标准差
            var = np.diag(S)
            std = np.sqrt(np.maximum(var, 1e-8))
            
            # 计算相关系数矩阵
            R = S / np.outer(std, std)
            
            # 平均相关系数 (排除对角线)
            mean_corr = (R.sum() - N) / (N * (N - 1)) if N > 1 else 0.0
            
            # 目标矩阵 F (常数相关系数)
            F = mean_corr * np.outer(std, std)
            np.fill_diagonal(F, var)
            
            # 计算渐近方差和 pi
            try:
                Z = X_demeaned[:, :, None] * X_demeaned[:, None, :] - S[None, :, :]
                pi_mat = np.mean(Z**2, axis=0)
                pi = pi_mat.sum()
            except MemoryError:
                pi = 0.0
                pi_mat = np.zeros((N, N))
                for i in range(N):
                    for j in range(N):
                        val = np.mean((X_demeaned[:, i] * X_demeaned[:, j] - S[i, j])**2)
                        pi_mat[i, j] = val
                        pi += val
            
            # 计算渐近协方差和 rho
            rho = 0.0
            for i in range(N):
                rho += pi_mat[i, i]
                for j in range(N):
                    if i == j:
                        continue
                    asy_cov_ii_ij = np.mean((X_demeaned[:, i]**2 - var[i]) * (X_demeaned[:, i] * X_demeaned[:, j] - S[i, j]))
                    asy_cov_jj_ij = np.mean((X_demeaned[:, j]**2 - var[j]) * (X_demeaned[:, i] * X_demeaned[:, j] - S[i, j]))
                    term = mean_corr * (std[j] / std[i] * asy_cov_ii_ij + std[i] / std[j] * asy_cov_jj_ij) / 2.0
                    rho += term
                    
            # 样本协方差与目标矩阵的平方距离 gamma
            gamma = np.sum((S - F)**2)
            
            if gamma == 0:
                delta = 0.0
            else:
                delta = (pi - rho) / T / gamma
                delta = max(0.0, min(1.0, delta))
                
            Sigma = delta * F + (1.0 - delta) * S
            return Sigma
        else:
            # 默认：如果不匹配常数相关系数，则采用简单的对角线收缩
            var = np.diag(S)
            F = np.diag(var)
            delta = 0.1
            Sigma = delta * F + (1.0 - delta) * S
            return Sigma

    def _solve_risk_parity(self, Sigma: np.ndarray) -> np.ndarray:
        import numpy as np
        N = Sigma.shape[0]
        diag_var = np.diag(Sigma)
        
        # 初始权重设置为逆波动率
        x = 1.0 / np.sqrt(np.maximum(diag_var, 1e-8))
        
        max_iter = 100
        tol = 1e-6
        for _ in range(max_iter):
            x_old = x.copy()
            for i in range(N):
                b = np.dot(Sigma[i], x) - Sigma[i, i] * x[i]
                a = Sigma[i, i]
                if a <= 1e-8:
                    a = 1e-8
                x[i] = (-b + np.sqrt(b**2 + 4 * a)) / (2 * a)
                
            if np.max(np.abs(x - x_old)) < tol:
                break
                
        weights = x / np.sum(x)
        return weights




class HierarchicalRiskParityStrategy(RiskParityStrategy):
    """
    基于层次风险平价 (HRP) 的多资产 ETF 组合优化策略 (HierarchicalRiskParityStrategy)
    
    相比于传统风险平价（RP），HRP 采用层次聚类将相关资产进行分群，然后通过准对角化和
    递归二分法，分配各层级的投资权重。这种方法在不计算逆协方差矩阵的情况下即可进行配置，
    从而有效避免了在资产高相关或协方差矩阵病态时的数学求解不稳定性，显著降低了样本外波动和换手率。
    """
    name = "hrp"
    version = "0.1.0"

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        import numpy as np
        
        rolling_window = int(context.params.get("rolling_window", context.params.get("ewma_span", 120)))
        min_periods = int(context.params.get("min_periods", context.params.get("ewma_min_periods", 20)))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        
        closes = {}
        for asset_id in universe:
            frame = context.data.frames.get(asset_id)
            if frame is None:
                return None
            col = "acc_nav" if (use_nav and "acc_nav" in frame.columns) else "close"
            history = frame[frame.index <= context.date][col]
            closes[asset_id] = history

        price_frame = pd.DataFrame(closes).dropna()
        if price_frame.empty:
            return None
            
        # 转换为 DatetimeIndex
        price_frame.index = pd.to_datetime(price_frame.index)
        
        # 处理不同的估计频率
        if estimation_freq == "weekly":
            price_frame = price_frame.resample("W").last().dropna()
            window = max(2, int(rolling_window / 5))
            min_p = max(2, int(min_periods / 5))
        elif estimation_freq == "monthly":
            try:
                price_frame = price_frame.resample("ME").last().dropna()
            except Exception:
                price_frame = price_frame.resample("M").last().dropna()
            window = max(2, int(rolling_window / 20))
            min_p = max(2, int(min_periods / 20))
        else:
            window = rolling_window
            min_p = min_periods

        if len(price_frame) < min_p + 1:
            return None
            
        # 计算收益率
        returns = price_frame.pct_change().dropna().tail(window)
        if len(returns) < min_p:
            return None
            
        # 提取收益率 numpy 数组
        X = returns.values
        T, N = X.shape
        if N <= 1:
            return TargetPortfolio({asset_id: 1.0 / max(1, N) for asset_id in universe})
            
        # 计算样本协方差矩阵和相关系数矩阵
        cov = np.cov(X, rowvar=False).reshape(N, N)
        # 避免单资产或极小方差除以0，添加微小扰动
        diag_var = np.diag(cov)
        std = np.sqrt(np.maximum(diag_var, 1e-8))
        corr = cov / np.outer(std, std)
        # 数值截断确保 corr 在 [-1, 1] 内
        corr_clipped = np.clip(corr, -1.0, 1.0)
        
        # 1. 距离矩阵计算 d_ij = sqrt( (1 - rho_ij) / 2 )
        D = np.sqrt(0.5 * (1.0 - corr_clipped))
        
        # 2. 凝聚层次聚类（Single Linkage 单联动）
        clusters = [[i] for i in range(N)]
        while len(clusters) > 1:
            min_dist = float('inf')
            best_p, best_q = -1, -1
            for p in range(len(clusters)):
                for q in range(p + 1, len(clusters)):
                    # 簇之间叶子节点两两距离的最小值
                    dist = min(D[i, j] for i in clusters[p] for j in clusters[q])
                    if dist < min_dist:
                        min_dist = dist
                        best_p, best_q = p, q
            # 合并簇
            c_p = clusters[best_p]
            c_q = clusters[best_q]
            clusters.pop(max(best_p, best_q))
            clusters.pop(min(best_p, best_q))
            clusters.append(c_p + c_q)
            
        # 凝聚树构建完成，此时 clusters[0] 便是准对角化 (Quasi-Diagonalization) 重新排序后的叶子节点序列
        quasi_order = clusters[0]
        
        # 3. 递归平分权重分配 (Recursive Bisection)
        weights = np.zeros(N)
        
        def recursive_bisection(order: list[int], w_factor: float) -> None:
            if len(order) == 0:
                return
            if len(order) == 1:
                weights[order[0]] = w_factor
                return
                
            # 二分拆分
            k = len(order) // 2
            left_order = order[:k]
            right_order = order[k:]
            
            # 计算左半部分的局部逆方差权重和虚拟投资组合方差
            cov_left = cov[np.ix_(left_order, left_order)]
            diag_left = np.diag(cov_left)
            inv_var_left = 1.0 / np.maximum(diag_left, 1e-8)
            w_left = inv_var_left / np.sum(inv_var_left)
            V_left = float(np.dot(w_left, np.dot(cov_left, w_left)))
            
            # 计算右半部分的局部逆方差权重和虚拟投资组合方差
            cov_right = cov[np.ix_(right_order, right_order)]
            diag_right = np.diag(cov_right)
            inv_var_right = 1.0 / np.maximum(diag_right, 1e-8)
            w_right = inv_var_right / np.sum(inv_var_right)
            V_right = float(np.dot(w_right, np.dot(cov_right, w_right)))
            
            # 计算左右两部分资产的分配比重
            if V_left + V_right <= 0:
                alpha = 0.5
            else:
                alpha = V_right / (V_left + V_right)
                
            recursive_bisection(left_order, w_factor * alpha)
            recursive_bisection(right_order, w_factor * (1.0 - alpha))
            
        # 开始递归分配
        recursive_bisection(quasi_order, 1.0)
        
        # 组合 HRP 目标资产权重
        return TargetPortfolio({asset_id: float(weights[i]) for i, asset_id in enumerate(universe)})



class RiskParityCVaRDynamicBudgetStrategy(RiskParityLWCovStrategy):
    """
    基于 CVaR 动态预算与波动率目标控制的风险平价策略 (RiskParityCVaRDynamicBudgetStrategy)
    
    本策略结合了四种核心量化设计思想以解决极端风险控制与过度交易痛点：
    1. 资产级 CVaR 风险测度：在滚动窗口内计算每个资产各自的历史模拟条件风险价值 (CVaR)，捕捉尾部极端风险；
    2. 动态风险预算 (CVaR Dynamic Budget)：基于各资产的 CVaR 倒数动态分配其风险预算 (b_i)，降低极端风险高资产的风险预算；
    3. 协方差收缩与 CCD 求解：使用 Ledoit-Wolf 协方差收缩矩阵及 Cyclical Coordinate Descent (CCD) 算法进行精确、高稳定的风险平价求解；
    4. 组合波动率目标控制 (Volatility Targeting Overlay)：在资产权重确定后，通过预期组合年化波动率与目标波动率的比例，等比例缩放最终仓位以规避系统性大跌。
    """
    name = "risk_parity_cvar_dynamic_budget"
    version = "0.1.0"

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        import numpy as np
        
        rolling_window = int(context.params.get("rolling_window", context.params.get("ewma_span", 120)))
        min_periods = int(context.params.get("min_periods", context.params.get("ewma_min_periods", 20)))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        cov_estimator = context.params.get("cov_estimator", "ledoit_wolf")
        
        closes = {}
        for asset_id in universe:
            frame = context.data.frames.get(asset_id)
            if frame is None:
                return None
            col = "acc_nav" if (use_nav and "acc_nav" in frame.columns) else "close"
            history = frame[frame.index <= context.date][col]
            closes[asset_id] = history

        price_frame = pd.DataFrame(closes).dropna()
        if price_frame.empty:
            return None
            
        price_frame.index = pd.to_datetime(price_frame.index)
        
        if estimation_freq == "weekly":
            price_frame = price_frame.resample("W").last().dropna()
            window = max(2, int(rolling_window / 5))
            min_p = max(2, int(min_periods / 5))
        elif estimation_freq == "monthly":
            try:
                price_frame = price_frame.resample("ME").last().dropna()
            except Exception:
                price_frame = price_frame.resample("M").last().dropna()
            window = max(2, int(rolling_window / 20))
            min_p = max(2, int(min_periods / 20))
        else:
            window = rolling_window
            min_p = min_periods

        if len(price_frame) < min_p + 1:
            return None
            
        returns = price_frame.pct_change().dropna().tail(window)
        if len(returns) < min_p:
            return None
            
        X = returns.values
        T, N = X.shape
        if N == 0:
            return None
            
        # 1. 估算协方差矩阵
        if cov_estimator == "ledoit_wolf":
            Sigma = self._estimate_covariance(X, "constant_correlation")
        else:
            Sigma = np.cov(X, rowvar=False).reshape(N, N)
            
        # 2. 计算各资产自身的 CVaR
        confidence_level = float(context.params.get("confidence_level", 0.95))
        cvar_sensitivity = float(context.params.get("cvar_sensitivity", 1.0))
        
        cvars = []
        for i in range(N):
            asset_returns = X[:, i]
            losses = -asset_returns
            var_val = np.percentile(losses, confidence_level * 100)
            tail_losses = losses[losses >= var_val]
            if len(tail_losses) > 0:
                cvar_val = np.mean(tail_losses)
            else:
                cvar_val = var_val
            cvar_val = max(cvar_val, 1e-4)
            cvars.append(cvar_val)
            
        cvars = np.array(cvars)
        
        # 3. 计算动态风险预算 (b_i 与 CVaR^p 的倒数成正比)
        inv_cvar = 1.0 / cvars
        if cvar_sensitivity != 1.0:
            inv_cvar = inv_cvar ** cvar_sensitivity
        b_target = inv_cvar / np.sum(inv_cvar)
        
        # 4. 用动态 CCD 求解风险平价权重
        try:
            weights = self._solve_risk_parity_dynamic(Sigma, b_target)
        except Exception:
            weights = b_target.copy()
            
        # 5. 叠加波动率目标控制
        volatility_target = context.params.get("volatility_target", None)
        if volatility_target is not None:
            volatility_target = float(volatility_target)
            if volatility_target > 0:
                if estimation_freq == "weekly":
                    ann_factor = 52.0
                elif estimation_freq == "monthly":
                    ann_factor = 12.0
                else:
                    ann_factor = 252.0
                    
                Sigma_annual = Sigma * ann_factor
                portfolio_vol = np.sqrt(np.dot(weights, np.dot(Sigma_annual, weights)))
                
                scale_factor = min(1.0, volatility_target / portfolio_vol) if portfolio_vol > 0 else 1.0
                weights = weights * scale_factor

        return TargetPortfolio({asset_id: float(weights[i]) for i, asset_id in enumerate(universe)})

    def _solve_risk_parity_dynamic(self, Sigma: np.ndarray, b_target: np.ndarray) -> np.ndarray:
        import numpy as np
        N = Sigma.shape[0]
        diag_var = np.diag(Sigma)
        
        x = 1.0 / np.sqrt(np.maximum(diag_var, 1e-8))
        
        max_iter = 100
        tol = 1e-6
        for _ in range(max_iter):
            x_old = x.copy()
            for i in range(N):
                b = np.dot(Sigma[i], x) - Sigma[i, i] * x[i]
                a = Sigma[i, i]
                if a <= 1e-8:
                    a = 1e-8
                x[i] = (-b + np.sqrt(b**2 + 4 * a * b_target[i])) / (2 * a)
                
            if np.max(np.abs(x - x_old)) < tol:
                break
                
        weights = x / np.sum(x)
        return weights



class AdaptiveRiskDeviationVolatilityTriggeredStrategy(RiskParityLWCovStrategy):
    """
    基于自适应风险偏离阈值与系统波动触发的动态再平衡风险平价策略 (AdaptiveRiskDeviationVolatilityTriggeredStrategy)
    
    本策略在 Ledoit-Wolf 协方差收缩风险平价策略的基础上，引入了创新的自适应动态再平衡机制：
    1. 自适应偏离阈值 (Adaptive Threshold)：
       利用短期系统波动率（反映即期市场冲击与噪声）与长期系统波动率（反映历史常态波动中枢）的比值，
       动态调整权重偏离的容忍度阈值 theta_t。
       公式：theta_t = theta_0 * exp(gamma * (vol_ratio - 1.0))，其中 vol_ratio = vol_short / vol_long。
       当市场波动骤增时（vol_ratio > 1），主动调大容忍阈值，以避免组合在震荡市中因无谓噪声被反复触发调仓（即换手阻尼机制）；
       当市场极度平稳时（vol_ratio < 1），阈值恢复或微降，实现高精度微调。
    2. 系统波动触发机制 (Crisis Trigger / Systematic Volatility Trigger)：
       若短期波动率发生剧烈飙升，超过长期波动率 of K 倍（默认 2.0 倍），意味着发生了系统性黑天鹅危机。
       此时强制打破阻尼机制，立刻以最新数据重构风险暴露，实现危机下的主动防守与风险再分配。
    3. 自适应偏离度检测 (Adaptive Deviation Check)：
       对比当前持仓的实际组合权重与最新的目标风险平价权重，计算最大单资产权重偏离度 max_deviation。
       如果 max_deviation > theta_t，或已触发系统波动危机机制，则启动再平衡调仓。
    4. 波动率目标控制 (Volatility Targeting Overlay)：
       支持通过配置 volatility_target，对求出的风险平价权重进行等比例的下调放缩（余下持币），
       在系统性熊市中提供强有力的绝对回撤保护。
    """
    name = "adaptive_risk_deviation_volatility_triggered"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        # 首日初始化建仓标记，默认由 init_mode 参数控制
        context.runtime["opened"] = context.params.get("init_mode", "calculate") == "manual"
        # 动态再平衡需要每日检测，因此默认 rebalance_frequency 设置为 daily
        context.runtime["rebalance_frequency"] = context.params.get("rebalance_frequency", "daily")

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        # 调用基类 (RiskParityLWCovStrategy) 的求解器获得未经过波动率目标控制的原始风险平价权重
        target = super()._inverse_vol_target(context, universe)
        if target is None:
            return None
            
        # 如果配置中启用了 volatility_target，则执行波动率目标控制 (Volatility Targeting Overlay)
        volatility_target = context.params.get("volatility_target", None)
        if volatility_target is not None:
            volatility_target = float(volatility_target)
            if volatility_target > 0:
                import numpy as np
                rolling_window = int(context.params.get("rolling_window", 120))
                min_periods = int(context.params.get("min_periods", 20))
                use_nav = bool(context.params.get("use_nav", False))
                
                closes = {}
                for asset_id in universe:
                    frame = context.data.frames.get(asset_id)
                    if frame is None:
                        return target
                    col = "acc_nav" if (use_nav and "acc_nav" in frame.columns) else "close"
                    history = frame[frame.index <= context.date][col]
                    closes[asset_id] = history

                price_frame = pd.DataFrame(closes).dropna()
                if price_frame.empty:
                    return target
                price_frame.index = pd.to_datetime(price_frame.index)
                
                if len(price_frame) < min_periods + 1:
                    return target
                returns = price_frame.pct_change().dropna().tail(rolling_window)
                if len(returns) < min_periods:
                    return target
                    
                X = returns.values
                # 估计协方差矩阵并年化
                Sigma = self._estimate_covariance(X, context.params.get("shrinkage_target", "constant_correlation"))
                Sigma_annual = Sigma * 252.0
                
                weights = np.array([target.weights.get(asset_id, 0.0) for asset_id in universe])
                portfolio_vol = np.sqrt(np.dot(weights, np.dot(Sigma_annual, weights)))
                
                scale_factor = min(1.0, volatility_target / portfolio_vol) if portfolio_vol > 0 else 1.0
                
                # 等比例缩放目标资产的暴露仓位
                scaled_weights = {asset_id: float(target.weights[asset_id] * scale_factor) for asset_id in universe}
                return TargetPortfolio(scaled_weights)
                
        return target

    def generate_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        import numpy as np
        
        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets and asset_id not in context.state.cooldown_pool]
        if not universe:
            return None

        # 1. 首次建仓决策
        if not bool(context.runtime.get("opened", False)):
            target = self._initial_target(context, universe)
            if target is None:
                return None
            context.runtime["opened"] = True
            return target

        # 2. 是否是调仓检测日（在 daily 下，每天均是检测日）
        if not self._is_rebalance_day(context):
            return None

        # 3. 计算最新的风险平价目标权重
        target = self._inverse_vol_target(context, universe)
        if target is None:
            return None

        # 4. 获取当前组合中各资产的实际持仓权重
        prices = {asset_id: bar.close for asset_id, bar in context.bars.items()}
        current_weights = context.state.weights(prices)

        # 5. 估计短期和长期的协方差矩阵以测度系统波动状态
        rolling_window = int(context.params.get("rolling_window", 120))  # 长期波动中枢窗口
        short_window = int(context.params.get("short_window", 20))       # 短期冲击窗口
        min_periods = int(context.params.get("min_periods", 20))
        use_nav = bool(context.params.get("use_nav", False))
        
        closes = {}
        for asset_id in universe:
            frame = context.data.frames.get(asset_id)
            if frame is None:
                return None
            col = "acc_nav" if (use_nav and "acc_nav" in frame.columns) else "close"
            history = frame[frame.index <= context.date][col]
            closes[asset_id] = history

        price_frame = pd.DataFrame(closes).dropna()
        if price_frame.empty:
            return None
        price_frame.index = pd.to_datetime(price_frame.index)
        
        if len(price_frame) < min_periods + 1:
            return None
            
        returns = price_frame.pct_change().dropna()
        if len(returns) < min_periods:
            return None

        # 分别截取长期和短期窗口的收益率序列
        returns_long = returns.tail(rolling_window)
        returns_short = returns.tail(short_window)
        
        if len(returns_long) < min_periods or len(returns_short) < max(2, int(short_window / 2)):
            return None
            
        X_long = returns_long.values
        X_short = returns_short.values
        
        # 估计两套协方差矩阵（并年化，日频率取 252）
        shrinkage_target = context.params.get("shrinkage_target", "constant_correlation")
        Sigma_long = self._estimate_covariance(X_long, shrinkage_target) * 252.0
        Sigma_short = self._estimate_covariance(X_short, shrinkage_target) * 252.0
        
        # 提取当前组合在两个协方差矩阵下的年化预期波动率
        curr_w_vector = np.array([current_weights.get(asset_id, 0.0) for asset_id in universe])
        # 如果当前没有持仓，则以目标平价权重代入作为基准
        if np.sum(curr_w_vector) < 1e-4:
            curr_w_vector = np.array([target.weights.get(asset_id, 0.0) for asset_id in universe])
            curr_w_vector = curr_w_vector / np.sum(curr_w_vector)
            
        vol_long = np.sqrt(np.dot(curr_w_vector, np.dot(Sigma_long, curr_w_vector)))
        vol_short = np.sqrt(np.dot(curr_w_vector, np.dot(Sigma_short, curr_w_vector)))
        
        if vol_long <= 1e-6:
            vol_long = 1e-6
            
        vol_ratio = vol_short / vol_long
        
        # 6. 确定自适应偏离容忍值
        rebalance_threshold_base = float(context.params.get("rebalance_threshold", 0.05))
        threshold_sensitivity = float(context.params.get("threshold_sensitivity", 1.0))
        
        # theta_t = theta_0 * exp(gamma * (vol_ratio - 1.0))
        adaptive_threshold = rebalance_threshold_base * np.exp(threshold_sensitivity * (vol_ratio - 1.0))
        
        # 对自适应阈值进行上下限截断，防止在极度波动或极度平稳时数值失真
        min_threshold = float(context.params.get("min_threshold", 0.01))
        max_threshold = float(context.params.get("max_threshold", 0.20))
        adaptive_threshold = np.clip(adaptive_threshold, min_threshold, max_threshold)
        
        # 7. 危机触发判定 (Crisis Trigger / Systematic Volatility Trigger)
        vol_trigger_ratio = float(context.params.get("vol_trigger_ratio", 2.0))
        crisis_triggered = vol_ratio > vol_trigger_ratio
        
        # 8. 计算实际持仓偏离度 (基于最大单资产权重绝对偏离)
        max_deviation = 0.0
        for asset_id, target_weight in target.weights.items():
            dev = abs(current_weights.get(asset_id, 0.0) - target_weight)
            if dev > max_deviation:
                max_deviation = dev
                
        # 9. 决策是否执行再平衡
        rebalance_triggered = (max_deviation > adaptive_threshold) or crisis_triggered
        
        if rebalance_triggered:
            context.runtime["last_rebalance_reason"] = "crisis" if crisis_triggered else f"deviation({max_deviation:.4f}>{adaptive_threshold:.4f})"
            return target
            
        return None

BUILTIN_STRATEGIES: dict[str, type[Strategy]] = {
    MonthlyEqualWeightStrategy.name: MonthlyEqualWeightStrategy,
    FundamentalValueEqualWeightStrategy.name: FundamentalValueEqualWeightStrategy,
    DriftRebalanceFixedWeightStrategy.name: DriftRebalanceFixedWeightStrategy,
    RiskParityStrategy.name: RiskParityStrategy,
    RiskParityEWMAStrategy.name: RiskParityEWMAStrategy,
    RiskParityEWMADrawdownRecoveryStrategy.name: RiskParityEWMADrawdownRecoveryStrategy,
    RiskParityLWCovStrategy.name: RiskParityLWCovStrategy,
    HierarchicalRiskParityStrategy.name: HierarchicalRiskParityStrategy,
    RiskParityCVaRDynamicBudgetStrategy.name: RiskParityCVaRDynamicBudgetStrategy,
    AdaptiveRiskDeviationVolatilityTriggeredStrategy.name: AdaptiveRiskDeviationVolatilityTriggeredStrategy,
}


def get_strategy_class(name: str) -> type[Strategy]:
    try:
        return BUILTIN_STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown platform strategy: {name}") from exc
