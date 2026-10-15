from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class PerformanceReport:
    total_return_pct: float
    max_drawdown_pct: float
    sharpe: float
    win_rate: float
    profit_factor: float
    trades: int
    final_equity: float
    avg_trade_pnl: float

    def to_dict(self) -> dict:
        return {
            "total_return_pct": round(self.total_return_pct, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "sharpe": round(self.sharpe, 2),
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2),
            "trades": self.trades,
            "final_equity": round(self.final_equity, 2),
            "avg_trade_pnl": round(self.avg_trade_pnl, 2),
        }


def max_drawdown_pct(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (peak - equity) / peak.replace(0, np.nan)
    return float(dd.max() * 100) if len(dd) else 0.0


def sharpe_ratio(returns: pd.Series, periods_per_year: float = 24 * 365) -> float:
    if returns.std() == 0 or returns.isna().all() or len(returns) < 2:
        return 0.0
    return float(returns.mean() / returns.std() * math.sqrt(periods_per_year))


def build_report(
    equity: pd.Series,
    trade_pnls: list[float],
    initial_capital: float,
) -> PerformanceReport:
    rets = equity.pct_change().dropna()
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p <= 0]
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    pf = (gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
    if math.isinf(pf):
        pf = 999.0

    return PerformanceReport(
        total_return_pct=((equity.iloc[-1] / initial_capital) - 1) * 100 if len(equity) else 0.0,
        max_drawdown_pct=max_drawdown_pct(equity),
        sharpe=sharpe_ratio(rets),
        win_rate=(len(wins) / len(trade_pnls) * 100) if trade_pnls else 0.0,
        profit_factor=pf,
        trades=len(trade_pnls),
        final_equity=float(equity.iloc[-1]) if len(equity) else initial_capital,
        avg_trade_pnl=(sum(trade_pnls) / len(trade_pnls)) if trade_pnls else 0.0,
    )
