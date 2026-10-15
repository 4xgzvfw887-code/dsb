from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from tradeforge.config import Settings


TIMEFRAME_TO_YF = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "1h",
    "1d": "1d",
}

SYMBOL_TO_YF = {
    "BTC/USDT": "BTC-USD",
    "ETH/USDT": "ETH-USD",
    "SOL/USDT": "SOL-USD",
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "SPY": "SPY",
}


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower(): c for c in df.columns}
    mapping = {}
    for need in ("open", "high", "low", "close", "volume"):
        if need in cols:
            mapping[cols[need]] = need
        elif need.title() in df.columns:
            mapping[need.title()] = need
    out = df.rename(columns=mapping)
    if not isinstance(out.index, pd.DatetimeIndex):
        if "timestamp" in out.columns:
            out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
            out = out.set_index("timestamp")
        else:
            out.index = pd.to_datetime(out.index, utc=True)
    out = out[["open", "high", "low", "close", "volume"]].astype(float)
    out = out.dropna().sort_index()
    return out


def generate_synthetic_ohlcv(
    bars: int = 500,
    start_price: float = 50_000.0,
    seed: int = 42,
    timeframe_minutes: int = 60,
) -> pd.DataFrame:
    """Deterministische Demo-Daten für Offline-Betrieb und Tests."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.00015, 0.008, size=bars)
    # leichter Trend + Mean-Reversion-Komponente
    noise = rng.normal(0, 0.002, size=bars)
    close = start_price * np.cumprod(1 + rets + noise)
    open_ = np.roll(close, 1)
    open_[0] = start_price
    high = np.maximum(open_, close) * (1 + rng.uniform(0.0005, 0.004, bars))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.0005, 0.004, bars))
    volume = rng.uniform(50, 500, bars) * close / start_price
    idx = pd.date_range(
        end=datetime.now(timezone.utc),
        periods=bars,
        freq=f"{timeframe_minutes}min",
        tz=timezone.utc,
    )
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def fetch_yfinance(symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
    import yfinance as yf

    yf_symbol = SYMBOL_TO_YF.get(symbol, symbol.replace("/", "-"))
    interval = TIMEFRAME_TO_YF.get(timeframe, "1h")
    period = "60d" if interval in {"1m", "5m", "15m", "1h"} else "2y"
    raw = yf.download(
        yf_symbol,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=True,
    )
    if raw.empty:
        raise RuntimeError(f"Keine Daten von yfinance für {yf_symbol}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0] for c in raw.columns]
    df = _normalize_ohlcv(raw)
    return df.tail(bars)


def fetch_ccxt(exchange_id: str, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
    import ccxt

    exchange_cls = getattr(ccxt, exchange_id, None)
    if exchange_cls is None:
        raise ValueError(f"Unbekannte Exchange: {exchange_id}")
    exchange = exchange_cls({"enableRateLimit": True})
    raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=min(bars, 1000))
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return _normalize_ohlcv(df)


def load_market_data(settings: "Settings") -> pd.DataFrame:
    source = settings.data.source.lower()
    bars = settings.data.history_bars
    if source == "demo":
        try:
            return fetch_yfinance(settings.symbol, settings.timeframe, bars)
        except Exception:
            minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}.get(
                settings.timeframe, 60
            )
            return generate_synthetic_ohlcv(bars=bars, timeframe_minutes=minutes)
    if source == "yfinance":
        return fetch_yfinance(settings.symbol, settings.timeframe, bars)
    if source == "exchange":
        return fetch_ccxt(settings.exchange, settings.symbol, settings.timeframe, bars)
    raise ValueError(f"Unbekannte data.source: {source}")
