from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from tradeforge.config import StrategyConfig
from tradeforge.models import Signal


class Strategy(ABC):
    name: str = "base"

    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    @abstractmethod
    def generate(self, df: pd.DataFrame, ml_proba: float | None = None) -> Signal:
        raise NotImplementedError
