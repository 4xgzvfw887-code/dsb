from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tradeforge.models import Trade


class TradeStore:
    def __init__(self, db_path: str) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    fee REAL NOT NULL,
                    pnl REAL NOT NULL,
                    reason TEXT,
                    status TEXT,
                    meta TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS equity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    equity REAL NOT NULL,
                    cash REAL NOT NULL,
                    note TEXT
                )
                """
            )

    def save_trade(self, trade: Trade) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO trades (timestamp, symbol, side, quantity, price, fee, pnl, reason, status, meta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.timestamp.isoformat(),
                    trade.symbol,
                    trade.side.value,
                    trade.quantity,
                    trade.price,
                    trade.fee,
                    trade.pnl,
                    trade.reason,
                    trade.status.value,
                    json.dumps(trade.meta),
                ),
            )

    def save_equity(self, equity: float, cash: float, note: str = "") -> None:
        from tradeforge.models import utcnow

        with self._conn() as conn:
            conn.execute(
                "INSERT INTO equity (timestamp, equity, cash, note) VALUES (?, ?, ?, ?)",
                (utcnow().isoformat(), equity, cash, note),
            )

    def list_trades(self, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM trades ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def equity_curve(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM equity ORDER BY id ASC").fetchall()
        return [dict(r) for r in rows]
