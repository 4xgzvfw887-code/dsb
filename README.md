# TradeForge AI

Verkaufsfähiger, modularer Trading-Bot mit **Paper-Trading**, **Backtesting**, **Ensemble-Strategien**, optionalem **ML-Score** und strengen **Risiko-Limits**.

> **Wichtig:** Kein Bot – auch keiner mit „KI“ – garantiert Gewinne. Märkte sind riskant. Starte immer im Paper-Modus. Siehe [docs/DISCLAIMER.md](docs/DISCLAIMER.md).

## Features

- Strategien: Momentum, Mean-Reversion, Ensemble
- Leichtes ML-Modell (Logistische Regression) für Richtungswahrscheinlichkeit
- Risiko-Engine: Positionsgröße, Stop/TP, Trailing, Tagesverlust- & Drawdown-Kill-Switch
- Paper-Broker (Simulation) und optional Live via ccxt
- SQLite-Trade-Log + Streamlit-Dashboard
- White-Label-Branding in der Config (zum Weiterverkaufen)

## Schnellstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Einstellungen ansehen
tradeforge info

# Historischen Backtest
tradeforge backtest

# Ein Paper-Trading-Zyklus
tradeforge paper --once

# Dashboard
tradeforge dashboard
```

Konfiguration: `config/default.yaml`  
Secrets (nur Live): `.env.example` → `.env`

## Live-Trading

1. Lange paper traden und Backtests prüfen  
2. API-Keys in `.env` setzen  
3. Nur mit bewusstem Risiko-Flag:

```bash
tradeforge live --i-understand-the-risk --once
```

Standardmäßig wird Sandbox genutzt, sofern die Exchange das unterstützt.

## Verkauf

Siehe [docs/SELLING.md](docs/SELLING.md). Du kannst die Software als Tool verkaufen – **nicht** als garantierte Geldmaschine.

## Tests

```bash
pytest -q
```

## Haftungsausschluss

Trading kann zu Verlusten bis zum Totalverlust führen. TradeForge AI ist keine Anlageberatung. Nutzung auf eigene Verantwortung.
