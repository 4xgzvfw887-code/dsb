from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from tradeforge.models import OrderStatus, Side, Trade, utcnow


@dataclass
class LiveBroker:
    """
    Live-Broker über ccxt.
    Erfordert API-Keys in der Umgebung. Standardmäßig Spot Market Orders.
    """

    exchange_id: str
    symbol: str
    sandbox: bool = True

    def __post_init__(self) -> None:
        import ccxt

        exchange_cls = getattr(ccxt, self.exchange_id, None)
        if exchange_cls is None:
            raise ValueError(f"Exchange nicht unterstützt: {self.exchange_id}")

        api_key = os.getenv("EXCHANGE_API_KEY", "")
        api_secret = os.getenv("EXCHANGE_API_SECRET", "")
        password = os.getenv("EXCHANGE_PASSWORD") or None

        if not api_key or not api_secret:
            raise RuntimeError(
                "Live-Modus benötigt EXCHANGE_API_KEY und EXCHANGE_API_SECRET in .env"
            )

        params: dict[str, Any] = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        }
        if password:
            params["password"] = password

        self.exchange = exchange_cls(params)
        if self.sandbox and hasattr(self.exchange, "set_sandbox_mode"):
            try:
                self.exchange.set_sandbox_mode(True)
            except Exception:
                pass

    def create_market_order(self, side: Side, quantity: float, reason: str = "") -> Trade:
        if side not in (Side.BUY, Side.SELL):
            raise ValueError("Ungültige Seite")
        order = self.exchange.create_order(self.symbol, "market", side.value, quantity)
        fill = float(order.get("average") or order.get("price") or 0)
        fee_cost = 0.0
        fee = order.get("fee") or {}
        if isinstance(fee, dict):
            fee_cost = float(fee.get("cost") or 0)
        return Trade(
            symbol=self.symbol,
            side=side,
            quantity=float(order.get("filled") or quantity),
            price=fill,
            fee=fee_cost,
            pnl=0.0,
            reason=reason,
            status=OrderStatus.FILLED,
            timestamp=utcnow(),
            meta={"order_id": order.get("id")},
        )
