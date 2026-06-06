from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import count

from src.platform_core.models import Asset, Bar, Order, PendingIntent, PortfolioState, TargetPortfolio, Trade


@dataclass(frozen=True)
class FeeProfile:
    rate: float = 0.0002
    min_fee: float = 0.0

    def calculate(self, trade_value: float) -> float:
        if trade_value <= 0:
            return 0.0
        return max(abs(trade_value) * self.rate, self.min_fee)


@dataclass(frozen=True)
class ExecutionConfig:
    fee_profile: FeeProfile
    price_field: str = "open_close_mid"
    weight_tolerance: float = 0.0005
    unfilled_policy: str = "retry_next_day"
    cash_buffer_pct: float = 0.0
    skip_below_lot: bool = True
    order_priority: str = "asset_id"


class ExecutionEngine:
    def __init__(self, config: ExecutionConfig):
        self.config = config
        self._order_ids = count(1)
        self._trade_ids = count(1)

    def apply_target(
        self,
        current_date: date,
        state: PortfolioState,
        assets: dict[str, Asset],
        bars: dict[str, Bar],
        target: TargetPortfolio,
        cooldown_days: int = 0,
        close_absent_positions: bool = True,
        signal_dates: dict[str, date] | None = None,
    ) -> tuple[list[Order], list[Trade]]:
        prices = {asset_id: self._price_for_bar(bar) for asset_id, bar in bars.items()}
        state_value = state.total_value(prices)
        orders: list[Order] = []
        trades: list[Trade] = []
        if state_value <= 0:
            return orders, trades

        buffer_scale = max(0.0, min(1.0, 1.0 - float(self.config.cash_buffer_pct)))
        effective_weights = {asset_id: weight * buffer_scale for asset_id, weight in target.weights.items()}

        for asset_id, target_weight in effective_weights.items():
            if asset_id not in assets:
                raise ValueError(f"Unknown asset in target portfolio: {asset_id}")

        target_asset_ids = set(effective_weights)
        if close_absent_positions:
            target_asset_ids.update(state.positions)
        trade_plan: list[tuple[str, float, float]] = []
        for asset_id in target_asset_ids:
            if asset_id not in bars:
                continue
            price = prices[asset_id]
            position = state.position(asset_id)
            current_value = position.quantity * price
            target_value = effective_weights.get(asset_id, 0.0) * state_value
            diff_value = target_value - current_value
            trade_plan.append((asset_id, diff_value, price))

        for asset_id, _, _ in self._sort_trade_plan(trade_plan):
            if asset_id not in bars:
                continue
            asset = assets[asset_id]
            bar = bars[asset_id]
            price = prices[asset_id]
            position = state.position(asset_id)
            current_value = position.quantity * price
            target_weight = effective_weights.get(asset_id, 0.0)
            target_value = target_weight * state_value
            diff_value = target_value - current_value
            if abs(diff_value / state_value) <= self.config.weight_tolerance:
                state.pending_intents.pop(asset_id, None)
                continue

            side = "BUY" if diff_value > 0 else "SELL"
            quantity = self._round_quantity(abs(diff_value) / price, asset.lot_size)
            if side == "SELL":
                quantity = min(quantity, self._round_quantity(position.quantity, asset.lot_size))
            one_lot_value = price * max(1, int(asset.lot_size))
            if self.config.skip_below_lot and quantity <= 0 and abs(diff_value) < one_lot_value:
                state.pending_intents.pop(asset_id, None)
                continue
            order = Order(
                order_id=f"O{next(self._order_ids):08d}",
                date=current_date,
                asset_id=asset_id,
                side=side,
                quantity=quantity,
                price=price,
                target_weight=target_weight,
                signal_date=self._signal_date_for(asset_id, current_date, state, signal_dates),
            )

            failure = self._validate_order(order, bar)
            if failure:
                order.status = "REJECTED"
                order.reason = failure
                orders.append(order)
                self._handle_unfilled(state, asset_id, target_weight, current_date, failure, order.signal_date)
                continue

            if side == "BUY":
                buy_cash = self._available_buy_cash(state.cash, state_value)
                quantity = self._cap_buy_quantity(quantity, price, buy_cash, asset.lot_size)
                order.quantity = quantity
            if quantity <= 0:
                if self.config.skip_below_lot and side == "BUY" and self._available_buy_cash(state.cash, state_value) < one_lot_value:
                    state.pending_intents.pop(asset_id, None)
                    continue
                order.status = "REJECTED"
                order.reason = "insufficient_cash_or_lot"
                orders.append(order)
                self._handle_unfilled(state, asset_id, target_weight, current_date, order.reason, order.signal_date)
                continue

            trade_value = quantity * price
            fee = self.config.fee_profile.calculate(trade_value)
            if side == "BUY":
                total_cost = trade_value + fee
                if total_cost > state.cash + 1e-9:
                    order.status = "REJECTED"
                    order.reason = "insufficient_cash"
                    orders.append(order)
                    self._handle_unfilled(state, asset_id, target_weight, current_date, order.reason, order.signal_date)
                    continue
                old_value = position.quantity * position.cost_basis
                state.cash -= total_cost
                position.quantity += quantity
                position.cost_basis = (old_value + trade_value) / position.quantity if position.quantity else 0.0
            else:
                if quantity > position.quantity + 1e-9:
                    order.status = "REJECTED"
                    order.reason = "insufficient_position"
                    orders.append(order)
                    self._handle_unfilled(state, asset_id, target_weight, current_date, order.reason, order.signal_date)
                    continue
                state.cash += trade_value - fee
                position.quantity -= quantity
                if position.quantity <= 1e-9:
                    position.quantity = 0.0
                    position.cost_basis = 0.0
                    if target_weight <= self.config.weight_tolerance and cooldown_days > 0:
                        state.cooldown_pool[asset_id] = cooldown_days

            order.status = "FILLED"
            orders.append(order)
            trade = Trade(
                trade_id=f"T{next(self._trade_ids):08d}",
                order_id=order.order_id,
                date=current_date,
                asset_id=asset_id,
                side=side,
                quantity=quantity,
                price=price,
                trade_value=trade_value,
                fee=fee,
                cash_after=state.cash,
                signal_date=order.signal_date,
            )
            trades.append(trade)

            post_prices = {item_id: self._price_for_bar(item_bar) for item_id, item_bar in bars.items()}
            post_value = state.total_value(post_prices)
            post_weight = position.quantity * price / post_value if post_value > 0 else 0.0
            if abs(post_weight - target_weight) <= self.config.weight_tolerance:
                state.pending_intents.pop(asset_id, None)
            else:
                self._handle_unfilled(state, asset_id, target_weight, current_date, "partial_fill", order.signal_date)

        return orders, trades

    def _price_for_bar(self, bar: Bar) -> float:
        field = self.config.price_field
        if field in {"open_close_mid", "oc_mid", "open_close_midpoint"}:
            return (float(bar.open) + float(bar.close)) / 2.0
        return float(getattr(bar, field))

    @staticmethod
    def _signal_date_for(
        asset_id: str,
        current_date: date,
        state: PortfolioState,
        signal_dates: dict[str, date] | None,
    ) -> date:
        if signal_dates and asset_id in signal_dates:
            return signal_dates[asset_id]
        intent = state.pending_intents.get(asset_id)
        if intent is not None:
            return intent.signal_date or intent.created_date
        return current_date

    def _available_buy_cash(self, cash: float, state_value: float) -> float:
        reserve = max(0.0, min(1.0, float(self.config.cash_buffer_pct))) * state_value
        return max(0.0, cash - reserve)

    def _sort_trade_plan(self, trade_plan: list[tuple[str, float, float]]) -> list[tuple[str, float, float]]:
        if self.config.order_priority == "target_gap_desc":
            return sorted(trade_plan, key=lambda item: (item[1] > 0, -abs(item[1]), -item[2], item[0]))
        if self.config.order_priority == "price_desc":
            return sorted(trade_plan, key=lambda item: (item[1] > 0, -item[2], -abs(item[1]), item[0]))
        return sorted(trade_plan, key=lambda item: item[0])

    @staticmethod
    def _round_quantity(quantity: float, lot_size: int) -> float:
        lot = max(1, int(lot_size))
        return float(int(quantity // lot) * lot)

    def _cap_buy_quantity(self, quantity: float, price: float, cash: float, lot_size: int) -> float:
        if quantity <= 0:
            return 0.0
        lot = max(1, int(lot_size))
        max_qty = int((cash / (price * (1 + self.config.fee_profile.rate))) // lot) * lot
        while max_qty > 0:
            value = max_qty * price
            if value + self.config.fee_profile.calculate(value) <= cash + 1e-9:
                break
            max_qty -= lot
        return float(min(quantity, max_qty))

    @staticmethod
    def _validate_order(order: Order, bar: Bar) -> str | None:
        if bar.is_suspended:
            return "suspended"
        if order.side == "BUY" and bar.limit_up is not None and order.price >= bar.limit_up * (1 - 1e-9):
            return "limit_up"
        if order.side == "SELL" and bar.limit_down is not None and order.price <= bar.limit_down * (1 + 1e-9):
            return "limit_down"
        return None

    def _handle_unfilled(
        self,
        state: PortfolioState,
        asset_id: str,
        target_weight: float,
        current_date: date,
        reason: str,
        signal_date: date | None = None,
    ) -> None:
        policy = self.config.unfilled_policy
        if policy == "retry_next_day":
            self._keep_pending(state, asset_id, target_weight, current_date, reason, signal_date)
            return
        state.pending_intents.pop(asset_id, None)
        if policy == "mark_failed":
            failures = state.strategy_state.setdefault("_execution_failed_intents", [])
            failures.append(
                {
                    "asset_id": asset_id,
                    "target_weight": target_weight,
                    "date": current_date.isoformat(),
                    "reason": reason,
                }
            )
            return
        if policy == "cancel":
            return
        raise ValueError(f"Unknown unfilled_policy: {policy}")

    @staticmethod
    def _keep_pending(
        state: PortfolioState,
        asset_id: str,
        target_weight: float,
        current_date: date,
        reason: str,
        signal_date: date | None = None,
    ) -> None:
        intent = state.pending_intents.get(asset_id)
        if intent is None:
            intent = PendingIntent(
                asset_id=asset_id,
                target_weight=target_weight,
                created_date=signal_date or current_date,
                signal_date=signal_date or current_date,
            )
            state.pending_intents[asset_id] = intent
        intent.target_weight = target_weight
        if signal_date is not None:
            intent.signal_date = intent.signal_date or signal_date
        intent.last_attempt_date = current_date
        intent.attempts += 1
        intent.reason = reason
