from __future__ import annotations

import pandas as pd

from tradeforge.config import StrategyConfig
from tradeforge.models import Side, Signal
from tradeforge.strategies.base import Strategy
from tradeforge.strategies.mean_reversion import MeanReversionStrategy
from tradeforge.strategies.momentum import MomentumStrategy


class EnsembleStrategy(Strategy):
    name = "ensemble"

    def __init__(self, config: StrategyConfig) -> None:
        super().__init__(config)
        self.momentum = MomentumStrategy(config)
        self.mean_rev = MeanReversionStrategy(config)

    def generate(self, df: pd.DataFrame, ml_proba: float | None = None) -> Signal:
        m = self.momentum.generate(df, ml_proba=ml_proba)
        r = self.mean_rev.generate(df, ml_proba=ml_proba)

        # Momentum stärker in Trendmärkten, Mean-Reversion in Seitwärtsphasen
        row = df.iloc[-1]
        trend_strength = abs(float(row.get("ema_trend", 0) or 0))
        m_w = 0.65 if trend_strength > 0.01 else 0.45
        r_w = 1.0 - m_w

        def signed(sig: Signal) -> float:
            if sig.side == Side.BUY:
                return sig.confidence
            if sig.side == Side.SELL:
                return -sig.confidence
            return 0.0

        combined = m_w * signed(m) + r_w * signed(r)
        # Auf 0–1-Skala: |combined| ist bereits ~0–1, leicht strecken
        conf = min(0.99, abs(combined) * 1.35)

        if combined > 0.05:
            side = Side.BUY
        elif combined < -0.05:
            side = Side.SELL
        else:
            side = Side.FLAT
            conf = 0.0

        reason = f"ensemble mom=[{m.reason}] mr=[{r.reason}]"
        if ml_proba is not None:
            reason += f" | ML={ml_proba:.2f}"

        if side != Side.FLAT and conf < self.config.min_confidence:
            return Signal(Side.FLAT, 0.0, f"Konfidenz zu niedrig ({conf:.2f}): {reason}")

        return Signal(
            side=side,
            confidence=float(conf),
            reason=reason,
            meta={"combined": combined, "m_w": m_w, "r_w": r_w},
        )



def build_strategy(config: StrategyConfig) -> Strategy:
    name = (config.name or "ensemble").lower()
    if name == "momentum":
        return MomentumStrategy(config)
    if name in {"mean_reversion", "mean-reversion", "mr"}:
        return MeanReversionStrategy(config)
    return EnsembleStrategy(config)
