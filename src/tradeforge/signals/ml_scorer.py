from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from tradeforge.signals.features import FEATURE_COLUMNS


class MLScorer:
    """Leichtgewichtiges ML-Modell für Richtungswahrscheinlichkeit."""

    def __init__(self, horizon: int = 3) -> None:
        self.horizon = horizon
        self.model: Pipeline | None = None
        self._fitted_on = 0

    def _xy(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        feats = df[FEATURE_COLUMNS].copy()
        future = df["close"].shift(-self.horizon) / df["close"] - 1
        y = (future > 0).astype(int)
        mask = feats.notna().all(axis=1) & y.notna()
        return feats.loc[mask], y.loc[mask]

    def fit(self, df: pd.DataFrame) -> None:
        X, y = self._xy(df)
        if len(X) < 80 or y.nunique() < 2:
            self.model = None
            return
        pipe = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=500,
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        )
        pipe.fit(X.values, y.values)
        self.model = pipe
        self._fitted_on = len(X)

    def predict_proba_up(self, row: pd.Series) -> float | None:
        if self.model is None:
            return None
        try:
            x = row[FEATURE_COLUMNS].astype(float).values.reshape(1, -1)
            if np.isnan(x).any():
                return None
            proba = float(self.model.predict_proba(x)[0][1])
            return proba
        except Exception:
            return None
