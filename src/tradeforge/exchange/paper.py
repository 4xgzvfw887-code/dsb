from __future__ import annotations

from dataclasses import dataclass, field

from tradeforge.models import OrderStatus, Position, Side, Trade, utcnow


@dataclass
class PaperBroker:
    """Simulierter Broker – ideal für Tests, Demos und Verkaufs-Demos."""

    cash: float
    fee_rate: float = 0.001
    slippage_pct: float = 0.05
    positions: list[Position] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    symbol: str = "BTC/USDT"

    def mark_to_market(self, price: float) -> float:
        """Equity = freies Cash + Marktwert Longs − Verbindlichkeit Shorts."""
        eq = self.cash
        for p in self.positions:
            if p.side == Side.BUY:
                eq += p.quantity * price
            elif p.side == Side.SELL:
                # Short: beim Open wurden Erlöse dem Cash gutgeschrieben.
                # Verbindlichkeit = aktuelle Rückkaufkosten.
                eq -= p.quantity * price
        return eq

    def _slip(self, price: float, side: Side) -> float:
        slip = self.slippage_pct / 100
        return price * (1 + slip) if side == Side.BUY else price * (1 - slip)

    def open_position(
        self,
        side: Side,
        quantity: float,
        price: float,
        stop_loss: float,
        take_profit: float,
        reason: str,
    ) -> Trade | None:
        fill = self._slip(price, side)
        notional = fill * quantity
        fee = notional * self.fee_rate

        if side == Side.BUY:
            cost = notional + fee
            if cost > self.cash:
                return Trade(
                    symbol=self.symbol,
                    side=side,
                    quantity=quantity,
                    price=fill,
                    fee=fee,
                    pnl=0.0,
                    reason=reason,
                    status=OrderStatus.REJECTED,
                    meta={"error": "Nicht genug Cash"},
                )
            self.cash -= cost
        else:
            # Short: Verkaufserlös auf Cash, Gebühr abziehen
            if fee > self.cash + notional:
                return Trade(
                    symbol=self.symbol,
                    side=side,
                    quantity=quantity,
                    price=fill,
                    fee=fee,
                    pnl=0.0,
                    reason=reason,
                    status=OrderStatus.REJECTED,
                    meta={"error": "Nicht genug Cash für Short"},
                )
            self.cash += notional - fee

        pos = Position(
            symbol=self.symbol,
            side=side,
            quantity=quantity,
            entry_price=fill,
            stop_loss=stop_loss,
            take_profit=take_profit,
            opened_at=utcnow(),
            peak_price=fill,
        )
        self.positions.append(pos)
        trade = Trade(
            symbol=self.symbol,
            side=side,
            quantity=quantity,
            price=fill,
            fee=fee,
            pnl=0.0,
            reason=reason,
            status=OrderStatus.FILLED,
        )
        self.trades.append(trade)
        return trade

    def close_position(self, position: Position, price: float, reason: str) -> Trade:
        exit_side = Side.SELL if position.side == Side.BUY else Side.BUY
        fill = self._slip(price, exit_side)
        fee = fill * position.quantity * self.fee_rate

        if position.side == Side.BUY:
            proceeds = fill * position.quantity - fee
            self.cash += proceeds
            pnl = (fill - position.entry_price) * position.quantity - fee
            # Entry-Fee war schon beim Open vom Cash; approximieren wir in PnL zusätzlich
            pnl -= position.entry_price * position.quantity * self.fee_rate
        else:
            # Short schließen: zurückkaufen
            cost = fill * position.quantity + fee
            self.cash -= cost
            pnl = (position.entry_price - fill) * position.quantity - fee
            pnl -= position.entry_price * position.quantity * self.fee_rate

        if position in self.positions:
            self.positions.remove(position)

        trade = Trade(
            symbol=self.symbol,
            side=exit_side,
            quantity=position.quantity,
            price=fill,
            fee=fee,
            pnl=pnl,
            reason=reason,
            status=OrderStatus.FILLED,
            meta={"entry": position.entry_price, "exit_reason": reason},
        )
        self.trades.append(trade)
        return trade
