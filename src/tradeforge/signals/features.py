from __future__ import annotations

import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame, rsi_period: int = 14, ema_fast: int = 12, ema_slow: int = 26, atr_period: int = 14) -> pd.DataFrame:
    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]

    out["ema_fast"] = close.ewm(span=ema_fast, adjust=False).mean()
    out["ema_slow"] = close.ewm(span=ema_slow, adjust=False).mean()
    out["ema_trend"] = (out["ema_fast"] - out["ema_slow"]) / out["ema_slow"]

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(rsi_period).mean()
    loss = (-delta.clip(upper=0)).rolling(rsi_period).mean()
    rs = gain / loss.replace(0, np.nan)
    out["rsi"] = 100 - (100 / (1 + rs))

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr"] = tr.rolling(atr_period).mean()
    out["atr_pct"] = out["atr"] / close

    out["ret_1"] = close.pct_change(1)
    out["ret_5"] = close.pct_change(5)
    out["ret_10"] = close.pct_change(10)
    out["vol_20"] = out["ret_1"].rolling(20).std()
    out["mom_20"] = close / close.shift(20) - 1

    # Bollinger-ähnlich
    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    out["bb_z"] = (close - mid) / std.replace(0, np.nan)

    # Volumen-Impuls
    vol_ma = out["volume"].rolling(20).mean()
    out["vol_ratio"] = out["volume"] / vol_ma.replace(0, np.nan)

    return out


FEATURE_COLUMNS = [
    "ema_trend",
    "rsi",
    "atr_pct",
    "ret_1",
    "ret_5",
    "ret_10",
    "vol_20",
    "mom_20",
    "bb_z",
    "vol_ratio",
]
