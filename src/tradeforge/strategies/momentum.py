from __future__ import annotations

import pandas as pd

from tradeforge.models import Side, Signal
from tradeforge.strategies.base import Strategy


class MomentumStrategy(Strategy):
    name = "momentum"

    def generate(self, df: pd.DataFrame, ml_proba: float | None = None) -> Signal:
        row = df.iloc[-1]
        ema_trend = float(row.get("ema_trend", 0) or 0)
        mom = float(row.get("mom_20", 0) or 0)
        rsi = float(row.get("rsi", 50) or 50)
        vol_ratio = float(row.get("vol_ratio", 1) or 1)

        score = 0.0
        reasons: list[str] = []

        if ema_trend > 0.001 and mom > 0:
            score += 0.35
            reasons.append("Aufwärtstrend (EMA/Momentum)")
        elif ema_trend < -0.001 and mom < 0:
            score -= 0.35
            reasons.append("Abwärtstrend (EMA/Momentum)")

        if rsi > 55 and rsi < self.config.rsi_overbought:
            score += 0.2
            reasons.append("RSI bullisch")
        elif rsi < 45 and rsi > self.config.rsi_oversold:
            score -= 0.2
            reasons.append("RSI bärisch")

        if vol_ratio > 1.2:
            score *= 1.1
            reasons.append("Volumen-Bestätigung")

        if ml_proba is not None:
            # ML zieht Score Richtung Wahrscheinlichkeit
            score = 0.6 * score + 0.4 * (ml_proba - 0.5) * 2
            reasons.append(f"ML P(up)={ml_proba:.2f}")

        conf = min(0.99, abs(score))
        if score > 0.15:
            side = Side.BUY
        elif score < -0.15:
            side = Side.SELL
        else:
            side = Side.FLAT
            reasons.append("kein klarer Momentum-Edge")

        return Signal(side=side, confidence=conf if side != Side.FLAT else 0.0, reason="; ".join(reasons) or "neutral", meta={"score": score})
