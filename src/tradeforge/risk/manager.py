from __future__ import annotations

from dataclasses import dataclass, field

from tradeforge.config import RiskConfig
from tradeforge.models import Position, Side, Signal


@dataclass
class RiskDecision:
    allowed: bool
    quantity: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    reason: str = ""


@dataclass
class RiskManager:
    config: RiskConfig
    initial_capital: float
    peak_equity: float = 0.0
    day_start_equity: float = 0.0
    halted: bool = False
    halt_reason: str = ""
    _open: list[Position] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.peak_equity = self.initial_capital
        self.day_start_equity = self.initial_capital

    def reset_day(self, equity: float) -> None:
        self.day_start_equity = equity

    def update_equity(self, equity: float) -> None:
        self.peak_equity = max(self.peak_equity, equity)
        dd = self.drawdown_pct(equity)
        if dd >= self.config.max_drawdown_pct:
            self.halted = True
            self.halt_reason = f"Max-Drawdown erreicht ({dd:.2f}%)"
        daily_loss_pct = ((self.day_start_equity - equity) / self.day_start_equity) * 100
        if daily_loss_pct >= self.config.max_daily_loss_pct:
            self.halted = True
            self.halt_reason = f"Tagesverlust-Limit erreicht ({daily_loss_pct:.2f}%)"

    def drawdown_pct(self, equity: float) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return max(0.0, (self.peak_equity - equity) / self.peak_equity * 100)

    def sync_positions(self, positions: list[Position]) -> None:
        self._open = list(positions)

    def size_order(
        self,
        signal: Signal,
        price: float,
        equity: float,
        atr: float | None = None,
    ) -> RiskDecision:
        if self.halted:
            return RiskDecision(False, reason=self.halt_reason or "Bot gestoppt")
        if not signal.is_actionable:
            return RiskDecision(False, reason="Kein handelbares Signal")
        if len(self._open) >= self.config.max_open_positions:
            return RiskDecision(False, reason="Max. offene Positionen erreicht")
        if price <= 0 or equity <= 0:
            return RiskDecision(False, reason="Ungültiger Preis/Equity")

        # Stop-Distanz: ATR-basiert falls vorhanden, sonst %-Stop
        if atr and atr > 0:
            stop_dist = max(atr * 1.5, price * (self.config.stop_loss_pct / 100))
        else:
            stop_dist = price * (self.config.stop_loss_pct / 100)

        risk_budget = equity * (self.config.risk_per_trade_pct / 100)
        qty_by_risk = risk_budget / stop_dist if stop_dist > 0 else 0.0
        max_notional = equity * (self.config.max_position_pct / 100)
        qty_by_cap = max_notional / price
        quantity = max(0.0, min(qty_by_risk, qty_by_cap))

        if quantity * price < 10:
            return RiskDecision(False, reason="Positionsgröße zu klein")

        if signal.side == Side.BUY:
            stop = price - stop_dist
            tp = price * (1 + self.config.take_profit_pct / 100)
        else:
            stop = price + stop_dist
            tp = price * (1 - self.config.take_profit_pct / 100)

        return RiskDecision(
            allowed=True,
            quantity=round(quantity, 8),
            stop_loss=round(stop, 8),
            take_profit=round(tp, 8),
            reason="OK",
        )

    def update_trailing_stop(self, position: Position, price: float) -> Position:
        trail = self.config.trailing_stop_pct / 100
        if position.side == Side.BUY:
            peak = max(position.peak_price or position.entry_price, price)
            position.peak_price = peak
            trailed = peak * (1 - trail)
            position.stop_loss = max(position.stop_loss, trailed)
        elif position.side == Side.SELL:
            trough = min(position.peak_price or position.entry_price, price)
            position.peak_price = trough
            trailed = trough * (1 + trail)
            position.stop_loss = min(position.stop_loss, trailed)
        return position

    def should_exit(self, position: Position, price: float) -> tuple[bool, str]:
        if position.side == Side.BUY:
            if price <= position.stop_loss:
                return True, "stop_loss"
            if price >= position.take_profit:
                return True, "take_profit"
        elif position.side == Side.SELL:
            if price >= position.stop_loss:
                return True, "stop_loss"
            if price <= position.take_profit:
                return True, "take_profit"
        return False, ""
