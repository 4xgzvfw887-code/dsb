from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"
    FLAT = "flat"


class OrderStatus(str, Enum):
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class Signal:
    side: Side
    confidence: float
    reason: str
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        return self.side in (Side.BUY, Side.SELL) and self.confidence > 0


@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Position:
    symbol: str
    side: Side
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    opened_at: datetime = field(default_factory=utcnow)
    peak_price: float | None = None

    def unrealized_pnl(self, price: float) -> float:
        if self.side == Side.BUY:
            return (price - self.entry_price) * self.quantity
        if self.side == Side.SELL:
            return (self.entry_price - price) * self.quantity
        return 0.0

    def unrealized_pnl_pct(self, price: float) -> float:
        if self.entry_price <= 0 or self.quantity <= 0:
            return 0.0
        notional = self.entry_price * self.quantity
        return (self.unrealized_pnl(price) / notional) * 100.0


@dataclass
class Trade:
    symbol: str
    side: Side
    quantity: float
    price: float
    fee: float
    pnl: float
    reason: str
    status: OrderStatus = OrderStatus.FILLED
    timestamp: datetime = field(default_factory=utcnow)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioSnapshot:
    equity: float
    cash: float
    open_positions: int
    daily_pnl: float
    drawdown_pct: float
    timestamp: datetime = field(default_factory=utcnow)
