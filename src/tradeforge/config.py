from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"


@dataclass
class RiskConfig:
    risk_per_trade_pct: float = 1.0
    max_position_pct: float = 20.0
    max_open_positions: int = 3
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 4.0
    max_daily_loss_pct: float = 3.0
    max_drawdown_pct: float = 15.0
    trailing_stop_pct: float = 1.5


@dataclass
class StrategyConfig:
    name: str = "ensemble"
    lookback: int = 50
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    ema_fast: int = 12
    ema_slow: int = 26
    atr_period: int = 14
    min_confidence: float = 0.35


@dataclass
class MLConfig:
    enabled: bool = True
    retrain_every_bars: int = 100
    prediction_horizon: int = 3


@dataclass
class ExecutionConfig:
    poll_seconds: int = 30
    fee_rate: float = 0.001
    slippage_pct: float = 0.05


@dataclass
class DataConfig:
    source: str = "demo"
    history_bars: int = 500


@dataclass
class StorageConfig:
    db_path: str = "data/tradeforge.db"
    log_dir: str = "logs"


@dataclass
class BrandingConfig:
    product_name: str = "TradeForge AI"
    vendor_name: str = "Your Brand"
    support_email: str = "support@example.com"


@dataclass
class Settings:
    mode: str = "paper"
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    exchange: str = "binance"
    initial_capital: float = 10_000.0
    quote_currency: str = "USDT"
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    ml: MLConfig = field(default_factory=MLConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    data: DataConfig = field(default_factory=DataConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    branding: BrandingConfig = field(default_factory=BrandingConfig)

    @property
    def is_live(self) -> bool:
        return self.mode.lower() == "live"


def _merge_dataclass(cls: type, raw: dict[str, Any] | None):
    raw = raw or {}
    fields = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    return cls(**{k: v for k, v in raw.items() if k in fields})


def load_settings(path: str | Path | None = None) -> Settings:
    load_dotenv(ROOT / ".env")
    cfg_path = Path(path) if path else DEFAULT_CONFIG
    raw: dict[str, Any] = {}
    if cfg_path.exists():
        with cfg_path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

    settings = Settings(
        mode=str(raw.get("mode", "paper")),
        symbol=str(raw.get("symbol", "BTC/USDT")),
        timeframe=str(raw.get("timeframe", "1h")),
        exchange=str(raw.get("exchange", "binance")),
        initial_capital=float(raw.get("initial_capital", 10_000.0)),
        quote_currency=str(raw.get("quote_currency", "USDT")),
        risk=_merge_dataclass(RiskConfig, raw.get("risk")),
        strategy=_merge_dataclass(StrategyConfig, raw.get("strategy")),
        ml=_merge_dataclass(MLConfig, raw.get("ml")),
        execution=_merge_dataclass(ExecutionConfig, raw.get("execution")),
        data=_merge_dataclass(DataConfig, raw.get("data")),
        storage=_merge_dataclass(StorageConfig, raw.get("storage")),
        branding=_merge_dataclass(BrandingConfig, raw.get("branding")),
    )

    # Env overrides
    if os.getenv("TRADEFORGE_MODE"):
        settings.mode = os.environ["TRADEFORGE_MODE"]
    if os.getenv("TRADEFORGE_SYMBOL"):
        settings.symbol = os.environ["TRADEFORGE_SYMBOL"]

    return settings
