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


class RiskParityTurnoverConstrainedStrategy(RiskParityStrategy):
    """
    基于换手率惩罚的动态再平衡控制策略 (R002)
    在传统的风险平价（逆波动率）权重基础上，引入换手率的 L1 惩罚项以及硬性上限约束，
    使用 SLSQP 二次规划进行平滑渐进式调仓，避免频繁微调与单次冲击成本过大。
    """
    name = "risk_parity_turnover_constrained"
    version = "0.1.0"

    def generate_targets(self, context: StrategyContext) -> TargetPortfolio | None:
        universe = context.params.get("universe") or context.available_asset_ids()
        universe = [asset_id for asset_id in universe if asset_id in context.assets and asset_id not in context.state.cooldown_pool]
        if not universe:
            return None

        # 初始建仓逻辑（不施加换手率惩罚）
        if not bool(context.runtime.get("opened", False)):
            target = self._initial_target(context, universe)
            if target is None:
                return None
            context.runtime["opened"] = True
            return target

        # 检查是否是调仓日
        if not self._is_rebalance_day(context):
            return None

        # 计算无约束风险平价目标权重
        if "ewma_span" in context.params:
            target = RiskParityEWMAStrategy._inverse_vol_target(self, context, universe)
        else:
            target = RiskParityStrategy._inverse_vol_target(self, context, universe)
            
        if target is None:
            return None

        prices = {asset_id: bar.close for asset_id, bar in context.bars.items()}
        current_weights = context.state.weights(prices)

        # 检查是否满足偏离度阈值触发条件
        threshold = float(context.params.get("rebalance_threshold", 0.05))
        trigger = False
        for asset_id in universe:
            target_weight = target.weights.get(asset_id, 0.0)
            if abs(current_weights.get(asset_id, 0.0) - target_weight) > threshold:
                trigger = True
                break

        # 如果有当前持有的资产不在 universe 中，且其当前权重显著大于 0.01，也应触发调仓（需要卖出）
        if not trigger:
            for asset_id, w_curr in current_weights.items():
                if asset_id not in universe and w_curr > 0.01:
                    trigger = True
                    break

        if not trigger:
            return None

        # 触发调仓后，引入换手率惩罚优化
        import numpy as np
        from scipy.optimize import minimize

        lmbda = float(context.params.get("turnover_penalty_lambda", 0.01))
        max_turnover = context.params.get("max_turnover", None)
        if max_turnover is not None:
            max_turnover = float(max_turnover)

        # 构建资产全集（目标组合资产与当前持有资产的并集）
        all_assets = list(set(universe) | set(current_weights.keys()))
        all_assets.sort()  # 保证变量索引顺序确定
        n = len(all_assets)

        w_current_arr = np.array([current_weights.get(aid, 0.0) for aid in all_assets])
        w_target_arr = np.array([target.weights.get(aid, 0.0) if aid in universe else 0.0 for aid in all_assets])

        # 优化变量 x = [w (n), u (n), v (n)]
        # 初始值 w = w_current, u = 0, v = 0
        x0 = np.concatenate([w_current_arr, np.zeros(n), np.zeros(n)])

        # 目标函数：二次偏离惩罚 + 换手率 L1 惩罚
        def objective(x):
            w = x[:n]
            u = x[n:2*n]
            v = x[2*n:]
            dist = np.sum((w - w_target_arr) ** 2)
            penalty = lmbda * np.sum(u + v)
            return dist + penalty

        # 约束条件
        cons = []
        # 1. 权重之和为 1
        cons.append({
            'type': 'eq',
            'fun': lambda x: np.sum(x[:n]) - 1.0
        })
        # 2. 线性化绝对值约束: w - w_current - u + v = 0
        cons.append({
            'type': 'eq',
            'fun': lambda x: x[:n] - w_current_arr - x[n:2*n] + x[2*n:]
        })
        # 3. 换手率硬上限约束 (若设置了 max_turnover, 限制单边换手率 <= max_turnover, 即双边和 <= 2 * max_turnover)
        if max_turnover is not None and max_turnover > 0:
            cons.append({
                'type': 'ineq',
                'fun': lambda x: 2.0 * max_turnover - np.sum(x[n:])
            })

        # 变量边界
        bounds = []
        # w_i 边界：如果是目标资产则为 [0, 1]，如果不在目标资产中则强制为 0
        for aid in all_assets:
            if aid in universe:
                bounds.append((0.0, 1.0))
            else:
                bounds.append((0.0, 0.0))
        # u_i, v_i 边界：[0, None]
        for _ in range(2 * n):
            bounds.append((0.0, None))

        res = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=cons)
        
        if res.success:
            w_opt = res.x[:n]
            # 生成新目标权重字典
            opt_weights = {}
            for aid, w_val in zip(all_assets, w_opt):
                if w_val > 1e-5:
                    opt_weights[aid] = float(w_val)
            
            # 归一化以防止浮点数微小误差
            total_w = sum(opt_weights.values())
            if total_w > 0:
                opt_weights = {aid: w_val / total_w for aid, w_val in opt_weights.items()}
                
            # 检查与当前权重的差异，若没有显著变动则不调仓
            total_diff = sum(abs(opt_weights.get(aid, 0.0) - current_weights.get(aid, 0.0)) for aid in all_assets)
            if total_diff > 1e-4:
                return TargetPortfolio(opt_weights)
            else:
                return None
        else:
            # 若优化失败，降级回退到原始逆波动率加权
            return target


class RiskParityDynamicBudgetStrategy(RiskParityStrategy):
    name = "risk_parity_dynamic_budget"
    version = "0.1.0"

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        """
        实现结合趋势动量与波动率靶向的动态风险预算策略。
        
        数学原理：
        1. 趋势动量计算：
           计算过去 N 日（momentum_window，默认 60）的趋势动量 M_i。
           支持两种模式：
           - "return" (区间收益率)：M_i = P_i(t) / P_i(t-N) - 1
           - "ma_deviation" (均线偏离度)：M_i = P_i(t) / MA_i(t, N) - 1
        2. 动态风险预算（Risk Budget）分配：
           对每个资产，其风险预算因子 B_i = 1.0 + momentum_sensitivity * M_i。
           设定下限限制（避免预算为负数）：B_i = max(0.1, B_i)。
        3. 初始权重分配：
           w_i_raw ∝ B_i / \sigma_i，其中 \sigma_i 为过去 rolling_window 周期内估计的资产波动率。
           归一化：w_i_raw = w_i_raw / sum(w_i_raw)。
        4. 波动率靶向（Volatility Targeting）：
           计算组合在当前权重 w_i_raw 下的预期波动率 \sigma_p = sqrt(w^T * \Sigma * w)。
           其中 \Sigma 为过去 rolling_window 周期的协方差矩阵。
           年化组合波动率 \sigma_p_annual = \sigma_p * sqrt(annualization_factor)。
           杠杆因子 leverage = volatility_target / \sigma_p_annual。
           若不加杠杆，则限制 leverage = min(max_leverage, leverage)。
           最终权重 w_i_final = w_i_raw * leverage。
        """
        # 参数获取
        momentum_window = int(context.params.get("momentum_window", 60))
        momentum_sensitivity = float(context.params.get("momentum_sensitivity", 1.5))
        volatility_target = float(context.params.get("volatility_target", 0.08))
        momentum_type = context.params.get("momentum_type", "return")
        
        rolling_window = int(context.params.get("rolling_window", context.params.get("ewma_span", 120)))
        min_periods = int(context.params.get("min_periods", context.params.get("ewma_min_periods", 20)))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        max_leverage = float(context.params.get("max_leverage", 1.0))
        budget_min = float(context.params.get("budget_min", 0.1))

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

        # 调整估计周期与窗口
        if estimation_freq == "weekly":
            price_frame = price_frame.resample("W").last().dropna()
            window = max(2, int(rolling_window / 5))
            min_p = max(2, int(min_periods / 5))
            m_window = max(2, int(momentum_window / 5))
            annualization_factor = 52
        elif estimation_freq == "monthly":
            try:
                price_frame = price_frame.resample("ME").last().dropna()
            except Exception:
                price_frame = price_frame.resample("M").last().dropna()
            window = max(2, int(rolling_window / 20))
            min_p = max(2, int(min_periods / 20))
            m_window = max(2, int(momentum_window / 20))
            annualization_factor = 12
        else:
            window = rolling_window
            min_p = min_periods
            m_window = momentum_window
            annualization_factor = 252

        # 校验历史长度，需要满足至少估计窗口和动量窗口的要求
        required_len = max(min_p, window, m_window) + 1
        if len(price_frame) < required_len:
            return None

        returns_frame = price_frame.pct_change().dropna()
        if len(returns_frame) < min_p:
            return None

        # 1. 计算各资产动量 M_i
        momentum = {}
        for asset_id in universe:
            prices = price_frame[asset_id]
            if len(prices) < m_window + 1:
                momentum[asset_id] = 0.0
                continue
            
            curr_price = prices.iloc[-1]
            if momentum_type == "ma_deviation":
                ma_val = prices.tail(m_window).mean()
                m_i = (curr_price / ma_val - 1.0) if ma_val > 0 else 0.0
            else:  # "return"
                prev_price = prices.iloc[-(m_window + 1)]
                m_i = (curr_price / prev_price - 1.0) if prev_price > 0 else 0.0
            momentum[asset_id] = m_i

        # 2. 计算资产各自波动率与协方差矩阵
        volatility = returns_frame.tail(window).std()
        volatility = volatility[volatility > 0]
        if len(volatility) != len(universe):
            return None

        cov_matrix = returns_frame.tail(window).cov()
        if cov_matrix.empty or cov_matrix.isnull().values.any():
            return None

        # 3. 计算动态风险预算与初始权重 w_raw
        raw_weights_dict = {}
        for asset_id in universe:
            m_i = momentum.get(asset_id, 0.0)
            budget = max(budget_min, 1.0 + momentum_sensitivity * m_i)
            raw_weights_dict[asset_id] = budget / volatility[asset_id]

        sum_raw = sum(raw_weights_dict.values())
        if sum_raw == 0:
            return None

        raw_weights_series = pd.Series({asset_id: w / sum_raw for asset_id, w in raw_weights_dict.items()})

        # 4. 波动率靶向调节
        portfolio_variance = raw_weights_series.dot(cov_matrix).dot(raw_weights_series)
        if portfolio_variance <= 0:
            return None
        
        portfolio_vol = portfolio_variance ** 0.5
        portfolio_vol_annual = portfolio_vol * (annualization_factor ** 0.5)

        leverage = volatility_target / portfolio_vol_annual if portfolio_vol_annual > 0 else 0.0
        leverage = min(max_leverage, leverage)

        final_weights = {asset_id: float(raw_weights_series[asset_id] * leverage) for asset_id in universe}

        return TargetPortfolio(final_weights)




class RiskParityGarchSemiVarStrategy(RiskParityStrategy):
    """
    基于 GARCH(1,1) 与下行半方差的非对称风险平价策略 (R004)
    
    1. GARCH(1,1) 条件波动率预测：
       对各资产的历史收益率序列进行 GARCH(1,1) 参数估计，通过极大似然估计 (MLE) 得到时变方差参数 omega, alpha, beta，
       并预测下一期的条件波动率。这相比于传统的 rolling std 能够更快速地反应最新的时变波动聚集效应。
    2. 下行半方差与下行半协方差：
       只惩罚负收益率（下行波动），定义下行半收益率 D_i = min(R_i, 0)。
       计算资产间的下行半协方差矩阵 Sigma_D = (D^T * D) / T，并求出下行相关系数矩阵 R_D。
    3. 结合 GARCH 与下行相关性：
       重构非对称下行协方差矩阵：Sigma_ij = sigma_garch_i * sigma_garch_j * R_D_ij。
       利用 Cyclical Coordinate Descent (CCD) 求解非对称风险平价下的投资组合权重。
    """
    name = "risk_parity_garch_semivar"
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
            
        # 1. 估计各资产的 GARCH(1,1) 条件标准差
        garch_vols = []
        for i in range(N):
            r_asset = X[:, i]
            garch_vol = self._estimate_garch_vol(r_asset)
            garch_vols.append(garch_vol)
        garch_vols = np.array(garch_vols)
        
        # 2. 计算下行半协方差矩阵及下行相关系数矩阵
        # 下行半收益率 D_i = min(R_i, 0)
        D = np.minimum(X, 0.0)
        Sigma_D = np.dot(D.T, D) / T
        
        # 提取对角线下行标准差
        std_D = np.sqrt(np.diag(Sigma_D))
        std_D = np.maximum(std_D, 1e-8)  # 避免除以 0
        
        # 下行相关系数矩阵 R_D
        R_D = Sigma_D / np.outer(std_D, std_D)
        R_D = np.nan_to_num(R_D, nan=0.0)
        # 确保对角线为 1
        for i in range(N):
            R_D[i, i] = 1.0
            
        # 3. 重构非对称 GARCH 条件协方差矩阵 Sigma_GD
        Sigma_GD = np.outer(garch_vols, garch_vols) * R_D
        
        # 为了 CCD 算法数值稳定性，进行微量的收缩或正则化调整
        # 保证矩阵严格正定
        shrinkage = 0.05
        Sigma_GD = (1.0 - shrinkage) * Sigma_GD + shrinkage * np.diag(np.diag(Sigma_GD))
        Sigma_GD += 1e-8 * np.eye(N)
        
        # 4. 求解风险平价权重
        try:
            weights = self._solve_risk_parity_garch(Sigma_GD)
        except Exception as e:
            weights = np.ones(N) / N
            
        return TargetPortfolio({asset_id: float(weights[i]) for i, asset_id in enumerate(universe)})

    def _estimate_garch_vol(self, returns: np.ndarray) -> float:
        from scipy.optimize import minimize
        import numpy as np
        
        T = len(returns)
        variance_sample = np.var(returns)
        if variance_sample <= 0:
            return 1e-4
            
        # 负对数似然函数
        def garch_log_likelihood(params):
            omega, alpha, beta = params
            sigma2 = np.zeros(T)
            sigma2[0] = variance_sample
            for t in range(1, T):
                sigma2[t] = omega + alpha * (returns[t-1]**2) + beta * sigma2[t-1]
            
            sigma2 = np.maximum(sigma2, 1e-10)
            log_lik = 0.5 * np.sum(np.log(sigma2) + (returns**2) / sigma2)
            return log_lik

        # 初始参数，典型经验值
        x0 = [0.05 * variance_sample, 0.05, 0.90]
        # 边界
        bounds = [(1e-9, 1.0 * variance_sample), (1e-4, 0.3), (0.5, 0.98)]
        # 约束 alpha + beta <= 0.999 保证平稳性
        cons = ({'type': 'ineq', 'fun': lambda x: 0.999 - x[1] - x[2]})
        
        try:
            res = minimize(garch_log_likelihood, x0, method='SLSQP', bounds=bounds, constraints=cons, options={'maxiter': 50, 'ftol': 1e-4})
            if res.success:
                omega_opt, alpha_opt, beta_opt = res.x
                # 递推计算最新的条件方差
                sigma2_last = variance_sample
                for t in range(1, T):
                    sigma2_last = omega_opt + alpha_opt * (returns[t-1]**2) + beta_opt * sigma2_last
                next_var = omega_opt + alpha_opt * (returns[-1]**2) + beta_opt * sigma2_last
                return np.sqrt(max(1e-10, next_var))
        except Exception:
            pass
            
        # 降级：如果估计失败，直接返回样本标准差
        return np.std(returns)

    def _solve_risk_parity_garch(self, Sigma: np.ndarray) -> np.ndarray:
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


class RiskParityCVaRStrategy(RiskParityStrategy):
    """
    基于条件风险价值 (CVaR / Expected Shortfall) 的风险平价策略 (R005)
    
    传统风险平价基于正态分布假设（仅使用波动率），忽略了极端的尾部风险和非对称分布特征。
    本策略使用历史模拟法 (Historical Simulation) 计算投资组合的条件风险价值 (CVaR) 以及
    各资产对组合边际 CVaR 贡献 (Marginal CVaR Contribution)。
    通过非线性优化，使各资产的 CVaR 风险贡献均等化，从而在防御极端尾部冲击的同时释放上行潜力。
    """
    name = "risk_parity_cvar"
    version = "0.1.0"

    def _inverse_vol_target(self, context: StrategyContext, universe: list[str]) -> TargetPortfolio | None:
        import numpy as np
        from scipy.optimize import minimize
        
        rolling_window = int(context.params.get("rolling_window", 120))
        min_periods = int(context.params.get("min_periods", 20))
        use_nav = bool(context.params.get("use_nav", False))
        estimation_freq = context.params.get("estimation_freq", "daily")
        confidence_level = float(context.params.get("confidence_level", 0.95))
        
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
            
        X = returns.values
        T, N = X.shape
        if N == 0:
            return None
            
        # 求解 CVaR 风险平价权重
        # 风险预算默认为等预算 b_i = 1/N
        b = np.ones(N) / N
        
        # 定义目标函数
        def cvar_objective(w):
            sum_w = np.sum(w)
            if sum_w <= 0:
                return 1e5
            w_norm = w / sum_w
            r_p = np.dot(X, w_norm)
            losses = -r_p
            # 检查是否有 nan
            if np.isnan(losses).any():
                return 1e5
            var_val = np.percentile(losses, confidence_level * 100)
            mask = losses >= var_val
            if not np.any(mask):
                mask = np.zeros(len(losses), dtype=bool)
                mask[np.argmax(losses)] = True
            
            cvar_val = np.mean(losses[mask])
            if np.isnan(cvar_val) or cvar_val <= 0:
                cvar_val = 1e-8
                
            mrc = -np.mean(X[mask, :], axis=0)
            rc = w_norm * mrc
            
            # 使用 CVaR 进行归一化
            obj_val = np.sum((rc / cvar_val - b) ** 2)
            if np.isnan(obj_val):
                return 1e5
            return obj_val

        # 初始权重设置为逆波动率
        vols = np.std(X, axis=0)
        vols = np.where(vols > 0, vols, 1e-5)
        inv_vol = 1.0 / vols
        w0 = inv_vol / np.sum(inv_vol)
        
        # 约束条件与边界
        cons = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
        bounds = [(0.0, 1.0) for _ in range(N)]
        
        res = minimize(cvar_objective, w0, method='SLSQP', bounds=bounds, constraints=cons, options={'tol': 1e-6})
        
        if res.success:
            weights = res.x
            weights = np.maximum(0.0, weights)
            weights = weights / np.sum(weights)
        else:
            weights = w0

        return TargetPortfolio({asset_id: float(weights[i]) for i, asset_id in enumerate(universe)})

BUILTIN_STRATEGIES: dict[str, type[Strategy]] = {
    RiskParityCVaRStrategy.name: RiskParityCVaRStrategy,
    MonthlyEqualWeightStrategy.name: MonthlyEqualWeightStrategy,
    FundamentalValueEqualWeightStrategy.name: FundamentalValueEqualWeightStrategy,
    DriftRebalanceFixedWeightStrategy.name: DriftRebalanceFixedWeightStrategy,
    RiskParityStrategy.name: RiskParityStrategy,
    RiskParityEWMAStrategy.name: RiskParityEWMAStrategy,
    RiskParityEWMADrawdownRecoveryStrategy.name: RiskParityEWMADrawdownRecoveryStrategy,
    RiskParityLWCovStrategy.name: RiskParityLWCovStrategy,
    RiskParityTurnoverConstrainedStrategy.name: RiskParityTurnoverConstrainedStrategy,
    RiskParityDynamicBudgetStrategy.name: RiskParityDynamicBudgetStrategy,
    RiskParityGarchSemiVarStrategy.name: RiskParityGarchSemiVarStrategy,
}


def get_strategy_class(name: str) -> type[Strategy]:
    try:
        return BUILTIN_STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown platform strategy: {name}") from exc
