from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.platform_core.data import LocalCsvBarData
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




class Strategy:
    name = "base"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        return None

    def generate_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        if not self.should_check_rebalance(context):
            return None

        target = self.generate_theoretical_targets(context)
        if target is None:
            return None

        if self.should_rebalance(context, target):
            return self.post_process_target(context, target)

        return None

    def generate_theoretical_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        raise NotImplementedError

    def should_check_rebalance(self, context: StrategyContext) -> bool:
        return self._is_rebalance_day(context)

    def should_rebalance(self, context: StrategyContext, target: TargetPortfolio) -> bool:
        has_position = any(
            position.quantity > 1e-9 for position in context.state.positions.values()
        )
        if not has_position:
            return True

        abs_threshold = float(context.params.get("rebalance_threshold", 0.0))
        rel_threshold = float(context.params.get("rebalance_relative_threshold", 0.0))
        if abs_threshold <= 1e-9 and rel_threshold <= 1e-9:
            return True

        prices = {asset_id: bar.close for asset_id, bar in context.bars.items()}
        current_weights = context.state.weights(prices)
        all_assets = set(target.weights.keys()) | set(current_weights.keys())
        for asset_id in all_assets:
            target_weight = target.weights.get(asset_id, 0.0)
            curr_weight = current_weights.get(asset_id, 0.0)
            deviation = abs(curr_weight - target_weight)
            if abs_threshold > 1e-9 and deviation > abs_threshold:
                return True
            if rel_threshold > 1e-9:
                if target_weight <= 1e-9 and curr_weight > 1e-9:
                    return True
                if target_weight > 1e-9 and deviation > rel_threshold * target_weight:
                    return True
        return False



    def post_process_target(self, context: StrategyContext, target: TargetPortfolio) -> TargetPortfolio:
        return target

    @staticmethod
    def _calendar_index(context: StrategyContext) -> int:
        if context.data is None or not hasattr(context.data, "calendar") or context.data.calendar is None:
            return -1
        try:
            return context.data.calendar.index(context.date)
        except ValueError:
            return -1

    @staticmethod
    def _is_rebalance_day(context: StrategyContext) -> bool:
        if context.data is None or not hasattr(context.data, "calendar") or context.data.calendar is None:
            return True
        idx = Strategy._calendar_index(context)
        if idx < 0:
            return False
        if idx == len(context.data.calendar) - 1:
            return True
        current = context.date
        next_date = context.data.calendar[idx + 1]

        freq = context.runtime.get("rebalance_frequency", "quarterly")
        if freq == "daily":
            return True
        if freq == "semiannually":
            current_q = (current.month - 1) // 3
            next_q = (next_date.month - 1) // 3
            return current_q != next_q and current_q in (0, 2)
        elif freq == "monthly":
            return current.year != next_date.year or current.month != next_date.month
        else: # quarterly
            current_quarter = (current.month - 1) // 3
            next_quarter = (next_date.month - 1) // 3
            return current.year != next_date.year or current_quarter != next_quarter



class MonthlyEqualWeightStrategy(Strategy):
    name = "monthly_equal_weight"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        context.set_cooldown(int(context.params.get("cooldown_days", 0)))
        context.set_rebalance_frequency("monthly")

    def generate_theoretical_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets and asset_id not in context.state.cooldown_pool]
        return TargetPortfolio.equal_weight(universe)

    def should_check_rebalance(self, context: StrategyContext) -> bool:
        if not context.params.get("rebalance_on_start", True) and context.state.last_date is None:
            return False
        if context.state.last_date is not None and not context.is_month_end():
            return False
        return True


class RiskParityStrategy(Strategy):
    name = "risk_parity"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        context.runtime["opened"] = context.params.get("init_mode", "calculate") == "manual"
        context.runtime["rebalance_frequency"] = context.params.get("rebalance_frequency", "quarterly")

    def should_check_rebalance(self, context: StrategyContext) -> bool:
        if not bool(context.runtime.get("opened", False)):
            return True
        return self._is_rebalance_day(context)

    def generate_theoretical_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets and asset_id not in context.state.cooldown_pool]
        if not universe:
            return None

        if not bool(context.runtime.get("opened", False)):
            target = self._initial_target(context, universe)
            if target is not None:
                context.runtime["opened"] = True
            return target

        return self._inverse_vol_target(context, universe)



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
        import numpy as np
        
        rolling_window = int(context.params.get("rolling_window", context.params.get("ewma_span", 120)))
        min_periods = int(context.params.get("min_periods", context.params.get("ewma_min_periods", 20)))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        
        price_frame = context.data.get_price_frame(universe, context.date, use_nav=use_nav)
        if price_frame is None or price_frame.empty:
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
            
        vol_multipliers = context.params.get("vol_multipliers", {})
        if vol_multipliers:
            for col, mult in vol_multipliers.items():
                if col in returns.columns:
                    returns[col] = returns[col] * float(mult)
            
        X = returns.values
        T, N = X.shape
        if N == 0:
            return None
            
        Sigma = np.cov(X, rowvar=False)
        if N == 1:
            Sigma = np.array([[Sigma]])
            
        try:
            weights = self._solve_risk_parity(Sigma)
        except Exception:
            weights = np.ones(N) / N
            
        return TargetPortfolio({asset_id: float(weights[i]) for i, asset_id in enumerate(universe)})

    def _solve_risk_parity(self, Sigma: np.ndarray) -> np.ndarray:
        import numpy as np
        N = Sigma.shape[0]
        
        try:
            min_eig = np.min(np.real(np.linalg.eigvals(Sigma)))
            if min_eig < 1e-6:
                Sigma = Sigma + (1e-6 - min_eig) * np.eye(N)
        except Exception:
            Sigma = Sigma + 1e-6 * np.eye(N)
            
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
                
                discriminant = b**2 + 4 * a
                if discriminant < 0:
                    discriminant = 0.0
                x[i] = (-b + np.sqrt(discriminant)) / (2 * a)
                
            if np.max(np.abs(x - x_old)) < tol:
                break
                
        w = x / np.maximum(x.sum(), 1e-8)
        return w


class RiskParityEWMAStrategy(RiskParityStrategy):
    name = "risk_parity_ewma"
    version = "0.1.0"

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        ewma_span = int(context.params.get("ewma_span", 60))
        ewma_min_periods = int(context.params.get("ewma_min_periods", 20))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        
        price_frame = context.data.get_price_frame(universe, context.date, use_nav=use_nav)
        if price_frame is None or price_frame.empty:
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
        vol_multipliers = context.params.get("vol_multipliers", {})
        if vol_multipliers:
            for col, mult in vol_multipliers.items():
                if col in returns.columns:
                    returns[col] = returns[col] * float(mult)
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

        price_frame = context.data.get_price_frame(universe, context.date, use_nav=use_nav)
        if price_frame is None or price_frame.empty:
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
        vol_multipliers = context.params.get("vol_multipliers", {})
        if vol_multipliers:
            for col, mult in vol_multipliers.items():
                if col in returns.columns:
                    returns[col] = returns[col] * float(mult)
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
        
        price_frame = context.data.get_price_frame(universe, context.date, use_nav=use_nav)
        if price_frame is None or price_frame.empty:
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
        
        price_frame = context.data.get_price_frame(universe, context.date, use_nav=use_nav)
        if price_frame is None or price_frame.empty:
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
        
        price_frame = context.data.get_price_frame(universe, context.date, use_nav=use_nav)
        if price_frame is None or price_frame.empty:
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
                
                price_frame = context.data.get_price_frame(universe, context.date, use_nav=use_nav)
                if price_frame is None or price_frame.empty:
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

    def should_rebalance(self, context: StrategyContext, target: TargetPortfolio) -> bool:
        import numpy as np

        has_position = any(
            position.quantity > 1e-9 for position in context.state.positions.values()
        )
        if not has_position:
            return True

        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets and asset_id not in context.state.cooldown_pool]
        if not universe:
            return False

        # 1. 获取当前组合中各资产的实际持仓权重
        prices = {asset_id: bar.close for asset_id, bar in context.bars.items()}
        current_weights = context.state.weights(prices)

        # 2. 估计短期和长期的协方差矩阵以测度系统波动状态
        rolling_window = int(context.params.get("rolling_window", 120))  # 长期波动中枢窗口
        short_window = int(context.params.get("short_window", 20))       # 短期冲击窗口
        min_periods = int(context.params.get("min_periods", 20))
        use_nav = bool(context.params.get("use_nav", False))
        
        price_frame = context.data.get_price_frame(universe, context.date, use_nav=use_nav)
        if price_frame is None or price_frame.empty:
            return False
        price_frame.index = pd.to_datetime(price_frame.index)
        
        if len(price_frame) < min_periods + 1:
            return False
            
        returns = price_frame.pct_change().dropna()
        if len(returns) < min_periods:
            return False

        # 分别截取长期和短期窗口的收益率序列
        returns_long = returns.tail(rolling_window)
        returns_short = returns.tail(short_window)
        
        if len(returns_long) < min_periods or len(returns_short) < max(2, int(short_window / 2)):
            return False
            
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
        
        # 3. 确定自适应偏离容忍值
        rebalance_threshold_base = float(context.params.get("rebalance_threshold", 0.05))
        threshold_sensitivity = float(context.params.get("threshold_sensitivity", 1.0))
        
        # theta_t = theta_0 * exp(gamma * (vol_ratio - 1.0))
        adaptive_threshold = rebalance_threshold_base * np.exp(threshold_sensitivity * (vol_ratio - 1.0))
        
        # 对自适应阈值进行上下限截断，防止在极度波动或极度平稳时数值失真
        min_threshold = float(context.params.get("min_threshold", 0.01))
        max_threshold = float(context.params.get("max_threshold", 0.20))
        adaptive_threshold = np.clip(adaptive_threshold, min_threshold, max_threshold)
        
        # 4. 危机触发判定 (Crisis Trigger / Systematic Volatility Trigger)
        vol_trigger_ratio = float(context.params.get("vol_trigger_ratio", 2.0))
        crisis_triggered = vol_ratio > vol_trigger_ratio
        
        # 5. 计算实际持仓偏离度 (基于最大单资产权重绝对偏离，考虑 target.weights 和 current_weights 并集)
        max_deviation = 0.0
        all_assets = set(target.weights.keys()) | set(current_weights.keys())
        for asset_id in all_assets:
            target_weight = target.weights.get(asset_id, 0.0)
            curr_weight = current_weights.get(asset_id, 0.0)
            dev = abs(curr_weight - target_weight)
            if dev > max_deviation:
                max_deviation = dev
                
        # 6. 决策是否执行再平衡
        rebalance_triggered = (max_deviation > adaptive_threshold) or crisis_triggered
        
        if rebalance_triggered:
            context.runtime["last_rebalance_reason"] = "crisis" if crisis_triggered else f"deviation({max_deviation:.4f}>{adaptive_threshold:.4f})"
            return True
            
        return False




class ClusterRepresentativeDampedRiskParityStrategy(RiskParityLWCovStrategy):
    """
    基于聚类代表性与切换阻尼的渐进式 ETF 筛选与轮动风险平价策略 (ClusterRepresentativeDampedRiskParityStrategy)
    
    本策略在 Ledoit-Wolf 协方差收缩风险平价的基础上，引入了两大核心创新设计以解决资产重合与过度换手痛点：
    1. 聚类代表性渐进式筛选 (Clustering Representativeness-based Screening)：
       - 根据传入的 sleeve_mapping 类别映射，或在策略内部基于相关性系数（阈值默认 0.70）进行在线动态聚类，将资产分为不同的风险类别。
       - 在每个聚类内部，计算各资产与其他资产的平均相关性绝对值作为代表性得分 (Representativeness Score)。
       - 渐进式筛选：每个聚类内仅保留得分排名前 top_k_per_sleeve (默认 1) 的代表性资产，其余资产予以剔除（权重设为 0.0），规避同质化资产的过度暴露。
    2. 双重切换阻尼控制 (Dual Switching Damping Control)：
       - 资产切换阻尼 (Switching Damping)：在更新入选资产池时，引入 switching_threshold (默认 0.05) 优惠。只有新资产得分显著高于已持有的旧资产时，才执行替换，防止临界点的频繁鞭梢切换。
       - 权重平滑阻尼 (Weight Smoothing Damping)：如果触发调仓，最终调仓权重按 damping_factor (lambda，默认 1.0) 进行渐进式过渡：
         w_actual = (1 - lambda) * w_current + lambda * w_target，从而极大地平滑调仓过程中的交易磨损。
    """
    name = "cluster_representative_damped_risk_parity"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        context.runtime["opened"] = context.params.get("init_mode", "calculate") == "manual"
        context.runtime["rebalance_frequency"] = context.params.get("rebalance_frequency", "daily")
        context.runtime["selected_assets"] = []  # 记录上一期入选的资产列表

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        import numpy as np
        
        rolling_window = int(context.params.get("rolling_window", context.params.get("ewma_span", 120)))
        min_periods = int(context.params.get("min_periods", context.params.get("ewma_min_periods", 20)))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        shrinkage_target = context.params.get("shrinkage_target", "constant_correlation")
        
        top_k = int(context.params.get("top_k_per_sleeve", 1))
        switching_threshold = float(context.params.get("switching_threshold", 0.05))
        sleeve_mapping = context.params.get("sleeve_mapping", None)
        
        price_frame = context.data.get_price_frame(universe, context.date, use_nav=use_nav)
        if price_frame is None or price_frame.empty:
            return None
            
        price_frame.index = pd.to_datetime(price_frame.index)
        
        # 频率调整
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
            
        # 1. 估算全量协方差矩阵与相关系数矩阵
        Sigma_full = self._estimate_covariance(X, shrinkage_target)
        
        # 提取标准差和相关系数矩阵
        std_full = np.sqrt(np.maximum(np.diag(Sigma_full), 1e-8))
        corr_full = Sigma_full / np.outer(std_full, std_full)
        corr_full = np.clip(corr_full, -1.0, 1.0)
        
        # 2. 确定资产所属的聚类（sleeve）
        if sleeve_mapping:
            # 建立类别到资产索引的映射
            categories = {}
            for i, asset_id in enumerate(universe):
                cat = sleeve_mapping.get(asset_id, "default_sleeve")
                categories.setdefault(cat, []).append(i)
        else:
            # 在线贪心聚类：如果两资产相关系数绝对值 >= 0.70，则归入同一聚类
            categories = {}
            visited = set()
            cat_count = 0
            for i in range(N):
                if i in visited:
                    continue
                cat_name = f"cluster_{cat_count}"
                categories[cat_name] = [i]
                visited.add(i)
                for j in range(i + 1, N):
                    if j not in visited and abs(corr_full[i, j]) >= 0.70:
                        categories[cat_name].append(j)
                        visited.add(j)
                cat_count += 1
                
        # 3. 计算每个资产在所属类别中的代表性得分 (同类资产平均相关性绝对值)
        rep_scores = np.zeros(N)
        for cat_name, idx_list in categories.items():
            if len(idx_list) <= 1:
                for idx in idx_list:
                    rep_scores[idx] = 1.0
            else:
                for idx in idx_list:
                    # 计算与本聚类内其他资产的平均绝对相关系数
                    others = [j for j in idx_list if j != idx]
                    rep_scores[idx] = np.mean(np.abs(corr_full[idx, others]))
                    
        # 4. 资产切换阻尼控制以决定入选的子资产池
        last_selected = context.runtime.setdefault("selected_assets", [])
        # 映射上一期入选资产的索引
        last_selected_indices = {universe.index(asset_id) for asset_id in last_selected if asset_id in universe}
        
        selected_indices = []
        for cat_name, idx_list in categories.items():
            # 计算本聚类内所有候选资产的调整得分
            adjusted_scores = []
            for idx in idx_list:
                score = rep_scores[idx]
                # 如果是上一期已入选的资产，增加切换优惠偏置
                if idx in last_selected_indices:
                    score += switching_threshold
                adjusted_scores.append((score, idx))
            
            # 按调整得分降序排列，选择前 top_k
            adjusted_scores.sort(key=lambda x: x[0], reverse=True)
            chosen = [idx for _, idx in adjusted_scores[:min(top_k, len(adjusted_scores))]]
            selected_indices.extend(chosen)
            
        # 记录本次入选的资产
        new_selected = [universe[idx] for idx in selected_indices]
        context.runtime["selected_assets"] = new_selected
        
        # 5. 对入选资产求解风险平价权重
        if not selected_indices:
            return None
            
        Sigma_sub = Sigma_full[np.ix_(selected_indices, selected_indices)]
        try:
            sub_weights = self._solve_risk_parity(Sigma_sub)
        except Exception:
            sub_weights = np.ones(len(selected_indices)) / len(selected_indices)
            
        # 将权重映射回全量资产
        weights_full = np.zeros(N)
        for i, idx in enumerate(selected_indices):
            weights_full[idx] = sub_weights[i]
            
        return TargetPortfolio({asset_id: float(weights_full[i]) for i, asset_id in enumerate(universe)})

    def should_rebalance(self, context: StrategyContext, target: TargetPortfolio) -> bool:
        prices = {asset_id: bar.close for asset_id, bar in context.bars.items()}
        current_weights = context.state.weights(prices)
        
        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets and asset_id not in context.state.cooldown_pool]

        # 判断是否有资产发生了进出变化（轮动）
        last_selected = context.runtime.get("selected_assets", [])
        current_selected = [asset_id for asset_id in universe if current_weights.get(asset_id, 0.0) > 1e-4]
        
        # 如果当前持仓的资产组合与筛选出来的资产组合不同，则必须触发调仓
        portfolio_changed = set(last_selected) != set(current_selected)
        deviation_triggered = super().should_rebalance(context, target)
        
        return portfolio_changed or deviation_triggered

    def post_process_target(self, context: StrategyContext, target: TargetPortfolio) -> TargetPortfolio:
        damping_factor = float(context.params.get("damping_factor", 1.0))
        if damping_factor < 1.0:
            prices = {asset_id: bar.close for asset_id, bar in context.bars.items()}
            current_weights = context.state.weights(prices)
            if current_weights:
                universe = context.params.get("universe") or context.available_asset_ids()
                universe = [asset_id for asset_id in universe if asset_id in context.assets and asset_id not in context.state.cooldown_pool]
                damped_weights = {}
                for asset_id in universe:
                    w_curr = current_weights.get(asset_id, 0.0)
                    w_targ = target.weights.get(asset_id, 0.0)
                    damped_weights[asset_id] = (1.0 - damping_factor) * w_curr + damping_factor * w_targ

                total_w = sum(damped_weights.values())
                if total_w > 1.0 + 1e-9:
                    damped_weights = {asset_id: w / total_w for asset_id, w in damped_weights.items()}
                return TargetPortfolio(damped_weights)
        return target


BUILTIN_STRATEGIES: dict[str, type[Strategy]] = {
    MonthlyEqualWeightStrategy.name: MonthlyEqualWeightStrategy,
    RiskParityStrategy.name: RiskParityStrategy,
    RiskParityEWMAStrategy.name: RiskParityEWMAStrategy,
    RiskParityEWMADrawdownRecoveryStrategy.name: RiskParityEWMADrawdownRecoveryStrategy,
    RiskParityLWCovStrategy.name: RiskParityLWCovStrategy,
    HierarchicalRiskParityStrategy.name: HierarchicalRiskParityStrategy,
    RiskParityCVaRDynamicBudgetStrategy.name: RiskParityCVaRDynamicBudgetStrategy,
    AdaptiveRiskDeviationVolatilityTriggeredStrategy.name: AdaptiveRiskDeviationVolatilityTriggeredStrategy,
    ClusterRepresentativeDampedRiskParityStrategy.name: ClusterRepresentativeDampedRiskParityStrategy,
}


def get_strategy_class(name: str) -> type[Strategy]:
    try:
        return BUILTIN_STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown platform strategy: {name}") from exc

class RiskParityGerberStrategy(RiskParityLWCovStrategy):
    """
    基于 Gerber 稳健统计量相关性过滤的风险平价策略 (RiskParityGerberStrategy)
    
    相比于传统的风险平价策略，本策略引入了 Gerber 稳健相关系数来过滤历史收益率中的噪声与异常值。
    当收益率绝对值超过设定的阈值时才被视为有显著运动，从而通过同向/异向显著运动天数占有效天数的比例
    计算相关性。对于可能不满足半正定（PSD）的 Gerber 相关系数矩阵，使用高稳定性谱裁剪与重构
    （Spectral Truncation and Renormalization）算法强制正定化，最终利用 CCD 算法精确求解风险平价权重。
    """
    name = "risk_parity_gerber"
    version = "0.1.0"

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        import numpy as np
        
        rolling_window = int(context.params.get("rolling_window", context.params.get("ewma_span", 120)))
        min_periods = int(context.params.get("min_periods", context.params.get("ewma_min_periods", 20)))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        gerber_c = float(context.params.get("gerber_c", 0.5))  # 阈值比例因子，默认 0.5
        
        price_frame = context.data.get_price_frame(universe, context.date, use_nav=use_nav)
        if price_frame is None or price_frame.empty:
            return None
            
        price_frame.index = pd.to_datetime(price_frame.index)
        
        # 频率调整
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
            
        # 1. 计算资产收益率样本标准差
        std = np.std(X, axis=0, ddof=1)
        std = np.maximum(std, 1e-8)  # 避免标准差为零
        
        # 2. 计算 Gerber 状态矩阵 U
        # 对每个资产，如果 R_t >= c * std_i，记为 1.0；如果 R_t <= -c * std_i，记为 -1.0；否则为 0.0
        U = np.zeros_like(X)
        for i in range(N):
            threshold = gerber_c * std[i]
            U[X[:, i] >= threshold, i] = 1.0
            U[X[:, i] <= -threshold, i] = -1.0
            
        # 3. 计算 Gerber 相关系数矩阵 G
        G = np.zeros((N, N))
        for i in range(N):
            for j in range(N):
                if i == j:
                    G[i, j] = 1.0
                    continue
                u_i = U[:, i]
                u_j = U[:, j]
                
                # 同号且不为0的时刻数
                n_plus = np.sum((u_i == u_j) & (u_i != 0.0))
                # 异号且不为0的时刻数
                n_minus = np.sum((u_i == -u_j) & (u_i != 0.0) & (u_j != 0.0))
                # 双方均落于中性区间的时刻数
                n_zero = np.sum((u_i == 0.0) & (u_j == 0.0))
                
                denom = n_plus + n_minus + n_zero
                if denom > 0:
                    G[i, j] = (n_plus - n_minus) / denom
                else:
                    G[i, j] = 0.0
                    
        # 4. 正定化相关系数矩阵 (Spectral Truncation and Renormalization)
        try:
            eigenvals, eigenvecs = np.linalg.eigh(G)
            eigenvals = np.maximum(eigenvals, 1e-8)
            G_clipped = eigenvecs @ np.diag(eigenvals) @ eigenvecs.T
            d_clipped = np.sqrt(np.diag(G_clipped))
            G_psd = G_clipped / np.outer(d_clipped, d_clipped)
            G_psd = (G_psd + G_psd.T) / 2.0
        except Exception:
            G_psd = np.eye(N)
            
        # 5. 构建协方差矩阵 Sigma = D * G_psd * D
        Sigma = np.diag(std) @ G_psd @ np.diag(std)
        
        # 6. 用 CCD 算法求解风险平价权重
        try:
            weights = self._solve_risk_parity(Sigma)
        except Exception:
            weights = np.ones(N) / N
            
        return TargetPortfolio({asset_id: float(weights[idx]) for idx, asset_id in enumerate(universe)})

BUILTIN_STRATEGIES[RiskParityGerberStrategy.name] = RiskParityGerberStrategy


class RiskParityEWMACovStrategy(RiskParityLWCovStrategy):
    """
    基于 EWMA 指数加权全协方差矩阵的风险平价策略 (RiskParityEWMACovStrategy)

    传统风险平价（risk_parity / risk_parity_lw_cov）在滚动窗口内对所有历史观测等权
    估计协方差，对近期的市场状态切换反应迟钝；而 risk_parity_ewma 虽对波动率做了
    EWMA 指数衰减加权，却仅用逆波动率（inverse-vol）配权，完全丢弃了资产间相关性信息。

    本策略采用经典 RiskMetrics 思路，对滚动窗口内的收益率施加指数时间衰减权重，
    同时估计**方差与相关性**构成的全协方差矩阵 Σ（近端观测权重更高），再叠加少量对角
    收缩以保证数值正定性，最后用 Cyclical Coordinate Descent (CCD) 求解等风险贡献权重。
    相比 Ledoit-Wolf，它对近期相关性结构变化更敏感；相比纯 EWMA 逆波动率，它保留了
    分散化所依赖的相关性结构。
    """
    name = "risk_parity_ewma_cov"
    version = "0.1.0"

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        import numpy as np

        rolling_window = int(context.params.get("rolling_window", context.params.get("ewma_span", 250)))
        min_periods = int(context.params.get("min_periods", context.params.get("ewma_min_periods", 20)))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        # EWMA 协方差的有效记忆跨度（span），span 越小越偏向近端观测
        ewma_cov_span = int(context.params.get("ewma_cov_span", context.params.get("ewma_span", 90)))
        # 对角收缩强度，保证 Σ 的数值正定与稳定（0 表示不收缩）
        shrinkage = float(context.params.get("ewma_cov_shrinkage", 0.1))

        price_frame = context.data.get_price_frame(universe, context.date, use_nav=use_nav)
        if price_frame is None or price_frame.empty:
            return None

        price_frame.index = pd.to_datetime(price_frame.index)

        if estimation_freq == "weekly":
            price_frame = price_frame.resample("W").last().dropna()
            window = max(2, int(rolling_window / 5))
            min_p = max(2, int(min_periods / 5))
            span = max(2, int(ewma_cov_span / 5))
        elif estimation_freq == "monthly":
            try:
                price_frame = price_frame.resample("ME").last().dropna()
            except Exception:
                price_frame = price_frame.resample("M").last().dropna()
            window = max(2, int(rolling_window / 20))
            min_p = max(2, int(min_periods / 20))
            span = max(2, int(ewma_cov_span / 20))
        else:
            window = rolling_window
            min_p = min_periods
            span = ewma_cov_span

        if len(price_frame) < min_p + 1:
            return None

        returns = price_frame.pct_change().dropna().tail(window)
        if len(returns) < min_p:
            return None

        X = returns.values
        T, N = X.shape
        if N == 0:
            return None

        # 1. 构造指数时间衰减权重（最近的观测权重最高）。span -> lambda 的标准换算。
        lam = 1.0 - 2.0 / (span + 1.0)
        lam = min(max(lam, 0.0), 0.9999)
        ages = np.arange(T - 1, -1, -1)  # 最旧观测 age 最大，权重最小
        w = lam ** ages
        w_sum = w.sum()
        if w_sum <= 0:
            w = np.ones(T) / T
        else:
            w = w / w_sum

        # 2. 加权去均值并估计 EWMA 全协方差矩阵 Σ = (X-μ)' diag(w) (X-μ)
        mu = np.average(X, axis=0, weights=w)
        Xd = X - mu
        Sigma = (Xd * w[:, None]).T @ Xd
        Sigma = (Sigma + Sigma.T) / 2.0  # 数值对称化

        # 3. 对角收缩（向各资产自身方差收缩），平滑相关性噪声并保证正定性
        if shrinkage > 0:
            D = np.diag(np.diag(Sigma))
            Sigma = (1.0 - shrinkage) * Sigma + shrinkage * D

        # 4. 用基类 CCD 求解器求解等风险贡献权重（含特征值正定化兜底）
        try:
            weights = self._solve_risk_parity(Sigma)
        except Exception:
            weights = np.ones(N) / N

        return TargetPortfolio({asset_id: float(weights[idx]) for idx, asset_id in enumerate(universe)})


BUILTIN_STRATEGIES[RiskParityEWMACovStrategy.name] = RiskParityEWMACovStrategy

# 扩展策略统一放在 strategies/ 包内（蓝图 C1 规范），在此 import 并注册
from src.platform_core.strategies.fixed_weight import FixedWeightThresholdStrategy  # noqa: E402

BUILTIN_STRATEGIES[FixedWeightThresholdStrategy.name] = FixedWeightThresholdStrategy
