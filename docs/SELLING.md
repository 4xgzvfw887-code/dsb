# TradeForge AI verkaufen – Checkliste

Dieses Repo ist als **verkauffähiges Produkt** aufgebaut (White-Label möglich).

## Was du verkaufen kannst

- Die Software-Lizenz (Nutzung des Bots, Dashboard, Backtester)
- Setup-Hilfe, Hosting, Support-Pakete
- Individuelle Strategie-Parameter / Branding (`config/default.yaml` → `branding`)

## Was du nicht verkaufen solltest

- „Garantierte Gewinne“ oder „passives Einkommen ohne Risiko“
- Signale als regulierte Anlageberatung ohne Erlaubnis
- Zugang zu Kunden-Exchange-Konten ohne klare Sicherheitsprozesse

## Empfohlene Produktstufen

| Stufe | Inhalt | Preisidee |
|-------|--------|-----------|
| Starter | Paper-Trading + Backtest + 1 Strategie | Einmallizenz |
| Pro | Ensemble + ML + Risiko-Limits + Dashboard | Abo / Einmal |
| Agency | White-Label, eigenes Branding, Support | höherer Abo-Preis |

## Branding anpassen

In `config/default.yaml`:

```yaml
branding:
  product_name: DeinBot AI
  vendor_name: Deine Firma
  support_email: support@deinedomain.de
```

## Rechtliches (kein Rechtsrat)

- Impressum / AGB / Widerruf (EU) wenn du online verkaufst
- Klarer Disclaimer (siehe `docs/DISCLAIMER.md`)
- Steuern & Gewerbeanmeldung je nach Land
- Bei Unsicherheit: Anwalt für IT-/Finanzrecht

## Demo für Kunden

```bash
pip install -e .
tradeforge backtest
tradeforge paper --once
tradeforge dashboard
```

Zeige immer zuerst Paper-Ergebnisse und Risiko-Metriken (Drawdown, Win Rate), nie nur „beste“ Return-Zahlen.
