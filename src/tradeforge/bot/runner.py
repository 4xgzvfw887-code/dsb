from __future__ import annotations

import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

from tradeforge.config import Settings, load_settings
from tradeforge.data.feed import load_market_data
from tradeforge.exchange.paper import PaperBroker
from tradeforge.models import Side
from tradeforge.risk.manager import RiskManager
from tradeforge.signals.features import add_indicators
from tradeforge.signals.ml_scorer import MLScorer
from tradeforge.storage.db import TradeStore
from tradeforge.strategies.ensemble import build_strategy

console = Console()


class BotRunner:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.store = TradeStore(self.settings.storage.db_path)
        Path(self.settings.storage.log_dir).mkdir(parents=True, exist_ok=True)
        self.broker = PaperBroker(
            cash=self.settings.initial_capital,
            fee_rate=self.settings.execution.fee_rate,
            slippage_pct=self.settings.execution.slippage_pct,
            symbol=self.settings.symbol,
        )
        self.risk = RiskManager(self.settings.risk, self.settings.initial_capital)
        self.strategy = build_strategy(self.settings.strategy)
        self.ml = MLScorer(self.settings.ml.prediction_horizon) if self.settings.ml.enabled else None
        self.live = None
        if self.settings.is_live:
            from tradeforge.exchange.live import LiveBroker

            console.print(
                "[bold red]LIVE-MODUS[/] – echte Orders möglich. "
                "Sandbox wird bevorzugt, sofern von der Exchange unterstützt."
            )
            self.live = LiveBroker(self.settings.exchange, self.settings.symbol, sandbox=True)

    def _prepare(self):
        df = load_market_data(self.settings)
        df = add_indicators(
            df,
            rsi_period=self.settings.strategy.rsi_period,
            ema_fast=self.settings.strategy.ema_fast,
            ema_slow=self.settings.strategy.ema_slow,
            atr_period=self.settings.strategy.atr_period,
        ).dropna()
        if self.ml:
            self.ml.fit(df)
        return df

    def once(self) -> dict:
        df = self._prepare()
        row = df.iloc[-1]
        price = float(row["close"])
        atr = float(row["atr"]) if row["atr"] == row["atr"] else None
        equity = self.broker.mark_to_market(price)
        self.risk.update_equity(equity)
        self.risk.sync_positions(self.broker.positions)

        # Trailing / Exits
        for pos in list(self.broker.positions):
            self.risk.update_trailing_stop(pos, price)
            exit_now, why = self.risk.should_exit(pos, price)
            if exit_now:
                trade = self.broker.close_position(pos, price, why)
                self.store.save_trade(trade)
                if self.live:
                    try:
                        side = Side.SELL if pos.side == Side.BUY else Side.BUY
                        self.live.create_market_order(side, pos.quantity, why)
                    except Exception as exc:  # noqa: BLE001
                        console.print(f"[red]Live-Exit fehlgeschlagen:[/] {exc}")

        ml_proba = self.ml.predict_proba_up(row) if self.ml else None
        signal = self.strategy.generate(df, ml_proba=ml_proba)
        decision = self.risk.size_order(signal, price, equity, atr=atr)

        opened = None
        if decision.allowed and not any(p.side == signal.side for p in self.broker.positions):
            opened = self.broker.open_position(
                signal.side,
                decision.quantity,
                price,
                decision.stop_loss,
                decision.take_profit,
                signal.reason,
            )
            if opened and opened.status.value == "filled":
                self.store.save_trade(opened)
                if self.live:
                    try:
                        self.live.create_market_order(signal.side, decision.quantity, signal.reason)
                    except Exception as exc:  # noqa: BLE001
                        console.print(f"[red]Live-Entry fehlgeschlagen:[/] {exc}")

        equity = self.broker.mark_to_market(price)
        self.store.save_equity(equity, self.broker.cash, note=signal.reason)

        return {
            "price": price,
            "signal": signal.side.value,
            "confidence": signal.confidence,
            "reason": signal.reason,
            "allowed": decision.allowed,
            "decision_reason": decision.reason,
            "equity": equity,
            "cash": self.broker.cash,
            "positions": len(self.broker.positions),
            "halted": self.risk.halted,
            "halt_reason": self.risk.halt_reason,
            "ml_proba": ml_proba,
            "opened": opened is not None,
        }

    def print_status(self, status: dict) -> None:
        table = Table(title=f"{self.settings.branding.product_name} – Status")
        table.add_column("Feld")
        table.add_column("Wert")
        for k, v in status.items():
            table.add_row(str(k), f"{v:.4f}" if isinstance(v, float) else str(v))
        console.print(table)

    def run_loop(self, iterations: int | None = None) -> None:
        mode = "LIVE" if self.settings.is_live else "PAPER"
        console.print(
            f"[bold]{self.settings.branding.product_name}[/] startet im [cyan]{mode}[/]-Modus "
            f"für {self.settings.symbol} ({self.settings.timeframe})"
        )
        console.print(
            "[yellow]Hinweis:[/] Kein Bot garantiert Gewinne. Nutze Paper-Trading und Risikolimits."
        )
        n = 0
        while iterations is None or n < iterations:
            try:
                status = self.once()
                self.print_status(status)
                if status["halted"]:
                    console.print(f"[red]Bot gestoppt:[/] {status['halt_reason']}")
                    break
            except Exception as exc:  # noqa: BLE001
                console.print(f"[red]Fehler im Zyklus:[/] {exc}")
            n += 1
            if iterations is not None and n >= iterations:
                break
            time.sleep(self.settings.execution.poll_seconds)
