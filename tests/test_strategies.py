import pandas as pd

from tradeforge.config import StrategyConfig
from tradeforge.data.feed import generate_synthetic_ohlcv
from tradeforge.models import Side
from tradeforge.signals.features import add_indicators
from tradeforge.strategies.ensemble import build_strategy


def test_ensemble_returns_signal():
    df = add_indicators(generate_synthetic_ohlcv(200)).dropna()
    strategy = build_strategy(StrategyConfig(name="ensemble", min_confidence=0.01))
    signal = strategy.generate(df)
    assert signal.side in {Side.BUY, Side.SELL, Side.FLAT}
    assert 0 <= signal.confidence <= 1
