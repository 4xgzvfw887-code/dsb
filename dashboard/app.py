from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tradeforge.backtest.engine import run_backtest
from tradeforge.config import load_settings
from tradeforge.data.feed import load_market_data
from tradeforge.storage.db import TradeStore

st.set_page_config(page_title="TradeForge AI", layout="wide")

settings = load_settings()
brand = settings.branding.product_name

st.title(brand)
st.caption(
    "Algorithmisches Trading-Toolkit mit Risiko-Limits, Paper-Trading und Backtests. "
    "Kein Finanzratgeber. Keine Gewinnversprechen."
)

tab_bt, tab_live, tab_risk = st.tabs(["Backtest", "Paper-Logs", "Risiko & Verkauf"])

with tab_bt:
    col1, col2, col3 = st.columns(3)
    with col1:
        symbol = st.text_input("Symbol", settings.symbol)
    with col2:
        strategy = st.selectbox("Strategie", ["ensemble", "momentum", "mean_reversion"], index=0)
    with col3:
        capital = st.number_input("Startkapital", value=float(settings.initial_capital), step=1000.0)

    if st.button("Backtest starten", type="primary"):
        cfg = load_settings()
        cfg.symbol = symbol
        cfg.strategy.name = strategy
        cfg.initial_capital = float(capital)
        with st.spinner("Marktdaten & Backtest …"):
            df = load_market_data(cfg)
            result = run_backtest(df, cfg)
        metrics = result.report.to_dict()
        mcols = st.columns(4)
        mcols[0].metric("Return %", metrics["total_return_pct"])
        mcols[1].metric("Max DD %", metrics["max_drawdown_pct"])
        mcols[2].metric("Sharpe", metrics["sharpe"])
        mcols[3].metric("Win Rate %", metrics["win_rate"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=result.equity_curve.index, y=result.equity_curve.values, name="Equity"))
        fig.update_layout(title="Equity-Kurve", height=420, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.json(metrics)
        st.info("Backtest-Ergebnisse sind historisch und keine Garantie für zukünftige Performance.")

with tab_live:
    store = TradeStore(settings.storage.db_path)
    trades = store.list_trades(200)
    equity = store.equity_curve()
    if equity:
        edf = pd.DataFrame(equity)
        st.line_chart(edf.set_index("timestamp")["equity"])
    else:
        st.write("Noch keine Equity-Daten. Starte `tradeforge paper --once`.")
    if trades:
        st.dataframe(pd.DataFrame(trades), use_container_width=True)
    else:
        st.write("Noch keine Trades gespeichert.")

with tab_risk:
    st.subheader("Eingebaute Risiko-Kontrolle")
    st.markdown(
        f"""
- Risiko pro Trade: **{settings.risk.risk_per_trade_pct}%**
- Max. Positionsgröße: **{settings.risk.max_position_pct}%**
- Stop-Loss / Take-Profit: **{settings.risk.stop_loss_pct}% / {settings.risk.take_profit_pct}%**
- Max. Tagesverlust: **{settings.risk.max_daily_loss_pct}%**
- Max. Drawdown: **{settings.risk.max_drawdown_pct}%**
        """
    )
    st.subheader("Verkaufshinweis")
    st.warning(
        "Du darfst diese Software als Tool verkaufen – aber **nicht** mit Garantie auf Gewinne. "
        "In vielen Ländern sind irreführende Renditeversprechen illegal. "
        "Nutze immer einen klaren Risiko-Disclaimer (siehe docs/DISCLAIMER.md)."
    )
