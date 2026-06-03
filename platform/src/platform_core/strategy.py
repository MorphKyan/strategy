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


BUILTIN_STRATEGIES: dict[str, type[Strategy]] = {
    MonthlyEqualWeightStrategy.name: MonthlyEqualWeightStrategy,
    FundamentalValueEqualWeightStrategy.name: FundamentalValueEqualWeightStrategy,
    DriftRebalanceFixedWeightStrategy.name: DriftRebalanceFixedWeightStrategy,
    RiskParityStrategy.name: RiskParityStrategy,
    RiskParityEWMAStrategy.name: RiskParityEWMAStrategy,
    RiskParityEWMADrawdownRecoveryStrategy.name: RiskParityEWMADrawdownRecoveryStrategy,
}


def get_strategy_class(name: str) -> type[Strategy]:
    try:
        return BUILTIN_STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown platform strategy: {name}") from exc
