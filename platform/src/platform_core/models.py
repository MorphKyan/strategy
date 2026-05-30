from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
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


@dataclass
class Position:
    asset_id: str
    quantity: float = 0.0
    cost_basis: float = 0.0

    def market_value(self, price: float) -> float:
        return self.quantity * price


@dataclass
class PendingIntent:
    asset_id: str
    target_weight: float
    created_date: date
    last_attempt_date: date | None = None
    attempts: int = 0
    reason: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "target_weight": self.target_weight,
            "created_date": date_str(self.created_date),
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

    def position(self, asset_id: str) -> Position:
        if asset_id not in self.positions:
            self.positions[asset_id] = Position(asset_id=asset_id)
        return self.positions[asset_id]

    def total_value(self, prices: dict[str, float]) -> float:
        value = self.cash
        for asset_id, position in self.positions.items():
            value += position.quantity * prices.get(asset_id, 0.0)
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
            "last_date": date_str(self.last_date),
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
            last_date=parse_date(payload["last_date"]) if payload.get("last_date") else None,
        )


@dataclass(frozen=True)
class TargetPortfolio:
    weights: dict[str, float]

    def __post_init__(self) -> None:
        total = 0.0
        for asset_id, weight in self.weights.items():
            if not asset_id:
                raise ValueError("TargetPortfolio asset_id cannot be empty.")
            if weight < -1e-12:
                raise ValueError(f"Negative target weight is not allowed: {asset_id}={weight}")
            total += weight
        if total > 1.0 + 1e-9:
            raise ValueError(f"Target weights cannot exceed 100%; got {total:.6f}")

    @classmethod
    def equal_weight(cls, asset_ids: list[str]) -> "TargetPortfolio":
        if not asset_ids:
            return cls({})
        weight = 1.0 / len(asset_ids)
        return cls({asset_id: weight for asset_id in asset_ids})


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
        }
