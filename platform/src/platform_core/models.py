from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from math import isfinite
from typing import Any


def parse_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def date_str(value: date | datetime | str | None) -> str | None:
    if value is None:
        return None
    return parse_date(value).isoformat()


@dataclass(frozen=True)
class Asset:
    asset_id: str
    code: str
    name: str
    asset_type: str = "etf"
    exchange: str = "CN"
    currency: str = "CNY"
    lot_size: int = 100
    price_limit_pct: float | None = 0.10

    def __post_init__(self) -> None:
        lot = float(self.lot_size)
        if not isfinite(lot) or not lot.is_integer() or lot <= 0:
            raise ValueError("Asset lot_size must be a positive integer.")
        object.__setattr__(self, "lot_size", int(lot))
        if not self.asset_id or not self.code:
            raise ValueError("Asset requires a nonempty asset_id and code.")
        if self.price_limit_pct is not None and not (
            isfinite(self.price_limit_pct) and 0 <= self.price_limit_pct <= 1
        ):
            raise ValueError("Asset price_limit_pct must be between 0 and 1, or None.")


@dataclass(frozen=True)
class Bar:
    date: date
    asset_id: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    amount: float = 0.0
    limit_up: float | None = None
    limit_down: float | None = None
    is_suspended: bool = False
    adj_close: float = 0.0


@dataclass
class Position:
    asset_id: str
    quantity: float = 0.0
    cost_basis: float = 0.0

@dataclass
class PendingIntent:
    asset_id: str
    target_weight: float
    created_date: date
    signal_date: date | None = None
    last_attempt_date: date | None = None
    attempts: int = 0
    reason: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "target_weight": self.target_weight,
            "created_date": date_str(self.created_date),
            "signal_date": date_str(self.signal_date or self.created_date),
            "last_attempt_date": date_str(self.last_attempt_date),
            "attempts": self.attempts,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PendingIntent":
        return cls(
            asset_id=payload["asset_id"],
            target_weight=float(payload["target_weight"]),
            created_date=parse_date(payload["created_date"]),
            signal_date=parse_date(payload["signal_date"]) if payload.get("signal_date") else parse_date(payload["created_date"]),
            last_attempt_date=parse_date(payload["last_attempt_date"]) if payload.get("last_attempt_date") else None,
            attempts=int(payload.get("attempts", 0)),
            reason=payload.get("reason", "pending"),
        )


@dataclass
class PortfolioState:
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    pending_intents: dict[str, PendingIntent] = field(default_factory=dict)
    cooldown_pool: dict[str, int] = field(default_factory=dict)
    strategy_state: dict[str, Any] = field(default_factory=dict)
    last_date: date | None = None
    dividend_receivables: list[dict[str, Any]] = field(default_factory=list)  # list of dict: {asset_id, payment_date, amount}
    live_accounting: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isfinite(self.cash):
            raise ValueError("Portfolio cash must be finite.")
        for asset_id, position in self.positions.items():
            if position.asset_id != asset_id:
                raise ValueError(f"Position asset_id does not match its key: {asset_id}")
            if any(not isfinite(value) or value < 0 for value in (position.quantity, position.cost_basis)):
                raise ValueError(f"Position quantity and cost must be finite and nonnegative: {asset_id}")
        for asset_id, intent in self.pending_intents.items():
            if intent.asset_id != asset_id:
                raise ValueError(f"Pending intent asset_id does not match its key: {asset_id}")
        TargetPortfolio({asset_id: intent.target_weight for asset_id, intent in self.pending_intents.items()})
        if any(not isfinite(float(item["amount"])) or float(item["amount"]) < 0 for item in self.dividend_receivables):
            raise ValueError("Dividend receivables must be finite and nonnegative.")

    def validate_assets(self, asset_ids: Any) -> None:
        held = {asset_id for asset_id, position in self.positions.items() if position.quantity > 0}
        unknown = (held | set(self.pending_intents)) - set(asset_ids)
        if unknown:
            raise ValueError(f"Portfolio contains assets missing from config: {sorted(unknown)}")

    def position(self, asset_id: str) -> Position:
        if asset_id not in self.positions:
            self.positions[asset_id] = Position(asset_id=asset_id)
        return self.positions[asset_id]

    def total_value(self, prices: dict[str, float]) -> float:
        value = self.cash
        for asset_id, position in self.positions.items():
            if not position.quantity:
                continue
            price = prices.get(asset_id)
            if price is None or not isfinite(price) or price <= 0:
                raise ValueError(f"Cannot value held asset without a finite positive price: {asset_id}")
            value += position.quantity * price
        for item in self.dividend_receivables:
            value += float(item.get("amount", 0.0))
        return value

    def weights(self, prices: dict[str, float]) -> dict[str, float]:
        total = self.total_value(prices)
        if total <= 0:
            return {asset_id: 0.0 for asset_id in self.positions}
        return {
            asset_id: position.quantity * prices.get(asset_id, 0.0) / total
            for asset_id, position in self.positions.items()
        }

    def decrement_cooldowns(self) -> None:
        expired = []
        for asset_id, days_left in self.cooldown_pool.items():
            next_value = max(0, int(days_left) - 1)
            self.cooldown_pool[asset_id] = next_value
            if next_value == 0:
                expired.append(asset_id)
        for asset_id in expired:
            del self.cooldown_pool[asset_id]

    def pending_target(self, current_date: date) -> TargetPortfolio | None:
        due = {asset_id: intent.target_weight for asset_id, intent in self.pending_intents.items()
               if intent.created_date < current_date}
        return TargetPortfolio(due) if due else None

    def pending_signal_dates(self, current_date: date) -> dict[str, date]:
        return {asset_id: intent.signal_date or intent.created_date
                for asset_id, intent in self.pending_intents.items() if intent.created_date < current_date}

    def replace_pending(self, target: TargetPortfolio, current_date: date) -> None:
        weights = dict(target.weights)
        for asset_id, position in self.positions.items():
            if position.quantity > 1e-9:
                weights.setdefault(asset_id, 0.0)
        self.pending_intents = {
            asset_id: PendingIntent(asset_id, weight, current_date, signal_date=current_date)
            for asset_id, weight in weights.items()
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "cash": self.cash,
            "positions": {
                asset_id: {
                    "asset_id": position.asset_id,
                    "quantity": position.quantity,
                    "cost_basis": position.cost_basis,
                }
                for asset_id, position in self.positions.items()
            },
            "pending_intents": {
                asset_id: intent.to_dict()
                for asset_id, intent in self.pending_intents.items()
            },
            "cooldown_pool": dict(self.cooldown_pool),
            "strategy_state": self.strategy_state,
            "live_accounting": self.live_accounting,
            "last_date": date_str(self.last_date),
            "dividend_receivables": [
                {
                    "asset_id": item["asset_id"],
                    "payment_date": date_str(item["payment_date"]),
                    "amount": float(item["amount"]),
                }
                for item in self.dividend_receivables
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PortfolioState":
        return cls(
            cash=float(payload["cash"]),
            positions={
                asset_id: Position(
                    asset_id=position.get("asset_id", asset_id),
                    quantity=float(position.get("quantity", 0.0)),
                    cost_basis=float(position.get("cost_basis", 0.0)),
                )
                for asset_id, position in payload.get("positions", {}).items()
            },
            pending_intents={
                asset_id: PendingIntent.from_dict(intent)
                for asset_id, intent in payload.get("pending_intents", {}).items()
            },
            cooldown_pool={asset_id: int(days) for asset_id, days in payload.get("cooldown_pool", {}).items()},
            strategy_state=payload.get("strategy_state", {}),
            live_accounting=payload.get("live_accounting", {}),
            last_date=parse_date(payload["last_date"]) if payload.get("last_date") else None,
            dividend_receivables=[
                {
                    "asset_id": item["asset_id"],
                    "payment_date": parse_date(item["payment_date"]),
                    "amount": float(item["amount"]),
                }
                for item in payload.get("dividend_receivables", [])
            ],
        )


@dataclass(frozen=True)
class TargetPortfolio:
    weights: dict[str, float]

    def __post_init__(self) -> None:
        total = 0.0
        for asset_id, weight in self.weights.items():
            if not asset_id:
                raise ValueError("TargetPortfolio asset_id cannot be empty.")
            if not isfinite(weight):
                raise ValueError(f"Target weight must be finite: {asset_id}={weight}")
            if weight < -1e-12:
                raise ValueError(f"Negative target weight is not allowed: {asset_id}={weight}")
            total += weight
        if total > 1.0 + 1e-9:
            raise ValueError(f"Target weights cannot exceed 100%; got {total:.6f}")

@dataclass
class Order:
    order_id: str
    date: date
    asset_id: str
    side: str
    quantity: float
    price: float
    status: str = "CREATED"
    reason: str = ""
    target_weight: float | None = None
    signal_date: date | None = None

    @property
    def trade_value(self) -> float:
        return abs(self.quantity * self.price)

    def to_row(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "date": date_str(self.date),
            "asset_id": self.asset_id,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "trade_value": self.trade_value,
            "status": self.status,
            "reason": self.reason,
            "target_weight": self.target_weight,
            "signal_date": date_str(self.signal_date),
        }


@dataclass
class Trade:
    trade_id: str
    order_id: str
    date: date
    asset_id: str
    side: str
    quantity: float
    price: float
    trade_value: float
    fee: float
    cash_after: float
    signal_date: date | None = None
    valuation_price: float | None = None

    def to_row(self) -> dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "date": date_str(self.date),
            "asset_id": self.asset_id,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "trade_value": self.trade_value,
            "fee": self.fee,
            "cash_after": self.cash_after,
            "signal_date": date_str(self.signal_date),
            "valuation_price": self.valuation_price,
        }
