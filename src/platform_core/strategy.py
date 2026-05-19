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


class RiskParityStrategy(Strategy):
    name = "risk_parity"
    version = "0.1.0"

    def initialize(self, context: StrategyContext) -> None:
        context.runtime["opened"] = context.params.get("init_mode", "calculate") == "manual"
        context.runtime["quarterly"] = True

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

        if not self._is_quarter_end(context):
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
        closes = {}
        for asset_id in universe:
            frame = context.data.frames.get(asset_id)
            if frame is None:
                return None
            history = frame[frame.index <= context.date]["close"].tail(rolling_window + 1)
            if len(history) < min_periods + 1:
                return None
            closes[asset_id] = history

        price_frame = pd.DataFrame(closes).dropna()
        if len(price_frame) < min_periods + 1:
            return None
        volatility = price_frame.pct_change().dropna().tail(rolling_window).std()
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
    def _is_quarter_end(context: StrategyContext) -> bool:
        idx = RiskParityStrategy._calendar_index(context)
        if idx < 0:
            return False
        if idx == len(context.data.calendar) - 1:
            return True
        current = context.date
        next_date = context.data.calendar[idx + 1]
        current_quarter = (current.month - 1) // 3
        next_quarter = (next_date.month - 1) // 3
        return current.year != next_date.year or current_quarter != next_quarter


BUILTIN_STRATEGIES: dict[str, type[Strategy]] = {
    MonthlyEqualWeightStrategy.name: MonthlyEqualWeightStrategy,
    FundamentalValueEqualWeightStrategy.name: FundamentalValueEqualWeightStrategy,
    RiskParityStrategy.name: RiskParityStrategy,
}


def get_strategy_class(name: str) -> type[Strategy]:
    try:
        return BUILTIN_STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown platform strategy: {name}") from exc
