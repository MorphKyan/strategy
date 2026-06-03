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
        rolling_window = int(context.params.get("rolling_window", 120))
        min_periods = int(context.params.get("min_periods", 20))
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
        
        # New parameters for Nonlinear Threshold and Trend Filter
        penalty_threshold = float(context.params.get("dd_penalty_threshold", 0.025))
        rebound_filter_window = int(context.params.get("rebound_filter_window", 0))

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
                
            # Apply rebound confirmation filter (Trend-Filtered Rebound)
            recovery = max(0.0, current_dd - min_dd)
            if rebound_filter_window > 0 and recovery > 0:
                # Calculate simple moving average on the raw price history
                ma_val = hist.tail(rebound_filter_window).mean() if len(hist) >= rebound_filter_window else curr_price
                if curr_price < ma_val:
                    # Price is below MA, filter out as a fake rebound (dead cat bounce)
                    recovery_term = 0.0
                else:
                    recovery_term = beta * recovery
            else:
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
        
        rolling_window = int(context.params.get("rolling_window", 120))
        min_periods = int(context.params.get("min_periods", 20))
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
        
        rolling_window = int(context.params.get("rolling_window", 120))
        min_periods = int(context.params.get("min_periods", 20))
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


BUILTIN_STRATEGIES: dict[str, type[Strategy]] = {
    MonthlyEqualWeightStrategy.name: MonthlyEqualWeightStrategy,
    FundamentalValueEqualWeightStrategy.name: FundamentalValueEqualWeightStrategy,
    DriftRebalanceFixedWeightStrategy.name: DriftRebalanceFixedWeightStrategy,
    RiskParityStrategy.name: RiskParityStrategy,
    RiskParityEWMAStrategy.name: RiskParityEWMAStrategy,
    RiskParityEWMADrawdownRecoveryStrategy.name: RiskParityEWMADrawdownRecoveryStrategy,
    RiskParityLWCovStrategy.name: RiskParityLWCovStrategy,
    RiskParityDynamicBudgetStrategy.name: RiskParityDynamicBudgetStrategy,
}


def get_strategy_class(name: str) -> type[Strategy]:
    try:
        return BUILTIN_STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown platform strategy: {name}") from exc
