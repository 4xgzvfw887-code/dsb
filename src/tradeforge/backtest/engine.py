from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from tradeforge.backtest.metrics import PerformanceReport, build_report
from tradeforge.config import Settings
from tradeforge.exchange.paper import PaperBroker
from tradeforge.models import Side
from tradeforge.risk.manager import RiskManager
from tradeforge.signals.features import add_indicators
from tradeforge.signals.ml_scorer import MLScorer
from tradeforge.strategies.ensemble import build_strategy


@dataclass
class BacktestResult:
    report: PerformanceReport
    equity_curve: pd.Series
    trades: list


def run_backtest(df: pd.DataFrame, settings: Settings) -> BacktestResult:
    cfg = settings
    data = add_indicators(
        df,
        rsi_period=cfg.strategy.rsi_period,
        ema_fast=cfg.strategy.ema_fast,
        ema_slow=cfg.strategy.ema_slow,
        atr_period=cfg.strategy.atr_period,
    ).dropna()

    broker = PaperBroker(
        cash=cfg.initial_capital,
        fee_rate=cfg.execution.fee_rate,
        slippage_pct=cfg.execution.slippage_pct,
        symbol=cfg.symbol,
    )
    risk = RiskManager(cfg.risk, cfg.initial_capital)
    strategy = build_strategy(cfg.strategy)
    ml = MLScorer(horizon=cfg.ml.prediction_horizon) if cfg.ml.enabled else None

    equity_points: list[float] = []
    equity_index: list = []
    closed_pnls: list[float] = []
    warmup = max(60, cfg.strategy.lookback)

    for i in range(warmup, len(data)):
        window = data.iloc[: i + 1]
        row = window.iloc[-1]
        price = float(row["close"])
        atr = float(row["atr"]) if not pd.isna(row["atr"]) else None

        if ml and (ml.model is None or i % cfg.ml.retrain_every_bars == 0):
            cut = cfg.ml.prediction_horizon
            train_df = window.iloc[:-cut] if cut > 0 else window
            ml.fit(train_df)

        # Exits zuerst
        risk.sync_positions(broker.positions)
        for pos in list(broker.positions):
            risk.update_trailing_stop(pos, price)
            exit_now, why = risk.should_exit(pos, price)
            if exit_now:
                trade = broker.close_position(pos, price, why)
                closed_pnls.append(trade.pnl)

        equity = broker.mark_to_market(price)
        risk.update_equity(equity)
        if risk.halted:
            equity_points.append(equity)
            equity_index.append(window.index[-1])
            continue

        ml_proba = ml.predict_proba_up(row) if ml else None
        signal = strategy.generate(window, ml_proba=ml_proba)

        # Nur eine Position pro Richtung in Backtest (vereinfacht)
        if signal.side == Side.BUY and any(p.side == Side.BUY for p in broker.positions):
            equity_points.append(equity)
            equity_index.append(window.index[-1])
            continue
        if signal.side == Side.SELL and any(p.side == Side.SELL for p in broker.positions):
            equity_points.append(equity)
            equity_index.append(window.index[-1])
            continue

        # Gegenposition schließen bei Flip
        if signal.side == Side.BUY:
            for pos in list(broker.positions):
                if pos.side == Side.SELL:
                    trade = broker.close_position(pos, price, "flip_to_long")
                    closed_pnls.append(trade.pnl)
        elif signal.side == Side.SELL:
            for pos in list(broker.positions):
                if pos.side == Side.BUY:
                    trade = broker.close_position(pos, price, "flip_to_short")
                    closed_pnls.append(trade.pnl)

        decision = risk.size_order(signal, price, equity, atr=atr)
        if decision.allowed:
            broker.open_position(
                signal.side,
                decision.quantity,
                price,
                decision.stop_loss,
                decision.take_profit,
                signal.reason,
            )

        equity = broker.mark_to_market(price)
        equity_points.append(equity)
        equity_index.append(window.index[-1])

    # Offene Positionen zum Schluss schließen
    if len(data):
        last_price = float(data.iloc[-1]["close"])
        for pos in list(broker.positions):
            trade = broker.close_position(pos, last_price, "backtest_end")
            closed_pnls.append(trade.pnl)
        if equity_points:
            equity_points[-1] = broker.mark_to_market(last_price)

    curve = pd.Series(equity_points, index=pd.Index(equity_index), name="equity")
    report = build_report(curve, closed_pnls, cfg.initial_capital)
    return BacktestResult(report=report, equity_curve=curve, trades=broker.trades)
