from __future__ import annotations

import pandas as pd

from tradeforge.models import Side, Signal
from tradeforge.strategies.base import Strategy


class MeanReversionStrategy(Strategy):
    name = "mean_reversion"

    def generate(self, df: pd.DataFrame, ml_proba: float | None = None) -> Signal:
        row = df.iloc[-1]
        rsi = float(row.get("rsi", 50) or 50)
        bb_z = float(row.get("bb_z", 0) or 0)
        atr_pct = float(row.get("atr_pct", 0) or 0)

        score = 0.0
        reasons: list[str] = []

        if rsi <= self.config.rsi_oversold or bb_z <= -1.5:
            score += 0.4
            reasons.append("überverkauft")
        elif rsi >= self.config.rsi_overbought or bb_z >= 1.5:
            score -= 0.4
            reasons.append("überkauft")

        # Extreme Volatilität → vorsichtiger
        if atr_pct > 0.03:
            score *= 0.7
            reasons.append("hohe Volatilität")

        if ml_proba is not None:
            # Mean-Reversion: leicht gegen starke ML-Richtung filtern
            score = 0.7 * score + 0.3 * (0.5 - ml_proba) * 2
            reasons.append(f"ML P(up)={ml_proba:.2f}")

        conf = min(0.99, abs(score))
        if score > 0.2:
            side = Side.BUY
        elif score < -0.2:
            side = Side.SELL
        else:
            side = Side.FLAT
            reasons.append("keine Mean-Reversion-Chance")

        return Signal(side=side, confidence=conf if side != Side.FLAT else 0.0, reason="; ".join(reasons) or "neutral", meta={"score": score})
