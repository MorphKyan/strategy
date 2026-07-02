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
    price_field: str = "open"
    weight_tolerance: float = 0.0005
    unfilled_policy: str = "retry_next_day"
    cash_buffer_pct: float = 0.0
    skip_below_lot: bool = True
    order_priority: str = "asset_id"
    slippage_bps: float = 2.0
    qdii_commodity_slippage_bps: float = 6.0
    slippage_by_asset_id: dict[str, float] | None = None
    slippage_by_code: dict[str, float] | None = None
    participation_impact: dict[str, float | bool] | None = None
    round_mode: str = "round"


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
        skipped_orders: list[Order] | None = None,
    ) -> tuple[list[Order], list[Trade]]:
        prices = {asset_id: self._price_for_bar(bar) for asset_id, bar in bars.items()}
        state_value = state.total_value(prices)
        orders: list[Order] = []
        trades: list[Trade] = []
        if state_value <= 0:
            return orders, trades

        target_sum = sum(target.weights.values())
        cash_buffer = float(self.config.cash_buffer_pct)
        if target_sum > 1.0 - cash_buffer:
            buffer_scale = min(1.0, (1.0 - cash_buffer) / target_sum)
        else:
            buffer_scale = 1.0
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
            valuation_price = prices[asset_id]
            position = state.position(asset_id)
            current_value = position.quantity * valuation_price
            target_weight = effective_weights.get(asset_id, 0.0)
            target_value = target_weight * state_value
            diff_value = target_value - current_value
            if abs(diff_value / state_value) <= self.config.weight_tolerance:
                state.pending_intents.pop(asset_id, None)
                continue

            side = "BUY" if diff_value > 0 else "SELL"
            planned_quantity = self._round_quantity(abs(diff_value) / valuation_price, asset.lot_size)
            if side == "SELL":
                planned_quantity = min(planned_quantity, self._round_quantity(position.quantity, asset.lot_size))
            execution_price = self._execution_price(valuation_price, side, asset, bar, planned_quantity)
            if side == "BUY" and bar.limit_up is not None:
                execution_price = min(execution_price, bar.limit_up)
            elif side == "SELL" and bar.limit_down is not None:
                execution_price = max(execution_price, bar.limit_down)
            quantity = planned_quantity
            one_lot_value = execution_price * max(1, int(asset.lot_size))
            if self.config.skip_below_lot and quantity <= 0 and abs(diff_value) < one_lot_value:
                state.pending_intents.pop(asset_id, None)
                continue
            order = Order(
                order_id=f"O{next(self._order_ids):08d}",
                date=current_date,
                asset_id=asset_id,
                side=side,
                quantity=quantity,
                price=execution_price,
                target_weight=target_weight,
                signal_date=self._signal_date_for(asset_id, current_date, state, signal_dates),
            )

            failure = self._validate_order(order, bar, valuation_price)
            if failure:
                order.status = "REJECTED"
                order.reason = failure
                orders.append(order)
                self._handle_unfilled(state, asset_id, target_weight, current_date, failure, order.signal_date)
                continue

            if side == "BUY":
                buy_cash = self._available_buy_cash(state.cash, state_value)
                quantity = self._cap_buy_quantity(quantity, execution_price, buy_cash, asset.lot_size)
                order.quantity = quantity
            if quantity <= 0:
                if side == "BUY":
                    order.status = "SKIPPED"
                    order.reason = "below_lot_or_cash"
                    state.pending_intents.pop(asset_id, None)
                    if skipped_orders is not None:
                        skipped_orders.append(order)
                    continue
                order.status = "REJECTED"
                order.reason = "insufficient_cash_or_lot"
                orders.append(order)
                self._handle_unfilled(state, asset_id, target_weight, current_date, order.reason, order.signal_date)
                continue

            trade_value = quantity * execution_price
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
                price=execution_price,
                trade_value=trade_value,
                fee=fee,
                cash_after=state.cash,
                signal_date=order.signal_date,
                valuation_price=valuation_price,
            )
            trades.append(trade)

            post_prices = {item_id: self._price_for_bar(item_bar) for item_id, item_bar in bars.items()}
            post_value = state.total_value(post_prices)
            post_weight = position.quantity * valuation_price / post_value if post_value > 0 else 0.0
            if abs(post_weight - target_weight) <= self.config.weight_tolerance:
                state.pending_intents.pop(asset_id, None)
            else:
                self._handle_unfilled(state, asset_id, target_weight, current_date, "partial_fill", order.signal_date)

        return orders, trades

    def _price_for_bar(self, bar: Bar) -> float:
        field = self.config.price_field
        return float(getattr(bar, field))

    def _execution_price(
        self,
        valuation_price: float,
        side: str,
        asset: Asset,
        bar: Bar | None = None,
        planned_quantity: float = 0.0,
    ) -> float:
        slippage = self._slippage_rate(asset, bar, planned_quantity, valuation_price)
        if side == "BUY":
            return valuation_price * (1.0 + slippage)
        return valuation_price * (1.0 - slippage)

    def _slippage_rate(
        self,
        asset: Asset,
        bar: Bar | None = None,
        planned_quantity: float = 0.0,
        valuation_price: float = 0.0,
    ) -> float:
        slippage_bps = self._slippage_bps(asset)
        slippage_bps += self._participation_impact_bps(bar, planned_quantity, valuation_price)
        return max(0.0, float(slippage_bps)) / 10000.0

    def _slippage_bps(self, asset: Asset) -> float:
        if self.config.slippage_by_asset_id:
            asset_overrides = {str(key): value for key, value in self.config.slippage_by_asset_id.items()}
            if asset.asset_id in asset_overrides:
                return float(asset_overrides[asset.asset_id])
        if self.config.slippage_by_code:
            code_overrides = {str(key): value for key, value in self.config.slippage_by_code.items()}
            if str(asset.code) in code_overrides:
                return float(code_overrides[str(asset.code)])
        if self._is_qdii_or_commodity(asset):
            return float(self.config.qdii_commodity_slippage_bps)
        return float(self.config.slippage_bps)

    def _participation_impact_bps(self, bar: Bar | None, planned_quantity: float, valuation_price: float) -> float:
        impact = self.config.participation_impact or {}
        if not bool(impact.get("enabled", False)):
            return 0.0
        trade_value = max(0.0, float(planned_quantity) * float(valuation_price))
        if trade_value <= 0:
            return 0.0
        amount = float(getattr(bar, "amount", 0.0) or 0.0) if bar is not None else 0.0
        if amount <= 0:
            return float(impact.get("missing_amount_extra_bps", 20.0))
        participation_rate = trade_value / amount
        free_rate = max(0.0, float(impact.get("free_participation_rate", 0.005)))
        excess_rate = max(0.0, participation_rate - free_rate)
        impact_bps = (excess_rate / 0.01) * float(impact.get("impact_bps_per_1pct", 5.0))
        return min(float(impact.get("max_impact_bps", 100.0)), max(0.0, impact_bps))

    @staticmethod
    def _is_qdii_or_commodity(asset: Asset) -> bool:
        asset_type = asset.asset_type.lower()
        if asset_type in {"qdii", "commodity", "commodity_etf", "qdii_etf"}:
            return True

        code = str(asset.code)
        if code.startswith("513") or code in {"159920", "159941", "159980", "159981", "159985", "518880"}:
            return True

        name = asset.name.lower()
        keywords = [
            "qdii",
            "纳指",
            "标普",
            "恒生",
            "港股",
            "日经",
            "德国",
            "法国",
            "海外",
            "黄金",
            "豆粕",
            "能源化工",
            "商品",
            "有色",
            "原油",
        ]
        return any(keyword in name for keyword in keywords)

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
        return sorted(trade_plan, key=lambda item: (item[1] > 0, item[0]))

    def _round_quantity(self, quantity: float, lot_size: int) -> float:
        lot = max(1, int(lot_size))
        round_mode = getattr(self.config, "round_mode", "round")
        if round_mode == "ceil":
            import math
            return float(math.ceil(quantity / lot) * lot)
        elif round_mode == "round":
            return float(int(quantity / lot + 0.5) * lot)
        else: # floor
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
    def _validate_order(order: Order, bar: Bar, valuation_price: float) -> str | None:
        if bar.is_suspended:
            return "suspended"
        if order.side == "BUY" and bar.limit_up is not None and valuation_price >= bar.limit_up * (1 - 1e-9):
            return "limit_up"
        if order.side == "SELL" and bar.limit_down is not None and valuation_price <= bar.limit_down * (1 + 1e-9):
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
