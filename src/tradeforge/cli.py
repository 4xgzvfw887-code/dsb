from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel

from tradeforge import PRODUCT_NAME, __version__
from tradeforge.backtest.engine import run_backtest
from tradeforge.bot.runner import BotRunner
from tradeforge.config import load_settings
from tradeforge.data.feed import load_market_data

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help=f"{PRODUCT_NAME} – Paper/Live Trading, Backtest & Dashboard",
)
console = Console()


def _banner() -> None:
    console.print(
        Panel.fit(
            f"[bold]{PRODUCT_NAME}[/] v{__version__}\n"
            "[dim]Tool, kein Gewinnversprechen. Märkte bergen Verlustrisiko.[/]",
            border_style="cyan",
        )
    )


@app.command("info")
def info(config: Optional[Path] = typer.Option(None, help="Pfad zur YAML-Config")) -> None:
    """Zeigt geladene Einstellungen."""
    _banner()
    settings = load_settings(config)
    console.print(
        JSON.from_data(
            {
                "mode": settings.mode,
                "symbol": settings.symbol,
                "timeframe": settings.timeframe,
                "strategy": settings.strategy.name,
                "initial_capital": settings.initial_capital,
                "data_source": settings.data.source,
                "product": settings.branding.product_name,
                "vendor": settings.branding.vendor_name,
            }
        )
    )


@app.command("backtest")
def backtest(
    config: Optional[Path] = typer.Option(None, help="Pfad zur YAML-Config"),
) -> None:
    """Führt einen historischen Backtest aus und zeigt Kennzahlen."""
    _banner()
    settings = load_settings(config)
    console.print(f"Lade Marktdaten für [cyan]{settings.symbol}[/] …")
    df = load_market_data(settings)
    console.print(f"{len(df)} Kerzen geladen. Starte Backtest ({settings.strategy.name}) …")
    result = run_backtest(df, settings)
    console.print(JSON.from_data(result.report.to_dict()))
    console.print(
        "[yellow]Backtest ≠ Zukunft.[/] Gute Kennzahlen sind kein Versprechen für Live-Gewinne."
    )


@app.command("paper")
def paper(
    config: Optional[Path] = typer.Option(None, help="Pfad zur YAML-Config"),
    once: bool = typer.Option(False, help="Nur einen Zyklus ausführen"),
    cycles: Optional[int] = typer.Option(None, help="Anzahl Zyklen"),
) -> None:
    """Startet den Bot im Paper-Trading (Simulation, kein echtes Geld)."""
    _banner()
    settings = load_settings(config)
    settings.mode = "paper"
    runner = BotRunner(settings)
    if once:
        status = runner.once()
        runner.print_status(status)
    else:
        runner.run_loop(iterations=cycles or (1 if once else None))


@app.command("live")
def live(
    config: Optional[Path] = typer.Option(None, help="Pfad zur YAML-Config"),
    confirm: bool = typer.Option(False, "--i-understand-the-risk", help="Risiko bestätigen"),
    once: bool = typer.Option(False, help="Nur einen Zyklus"),
) -> None:
    """Live-Trading (API-Keys nötig). Standard: Sandbox falls verfügbar."""
    _banner()
    if not confirm:
        console.print(
            "[red]Abbruch.[/] Live-Trading kann echtes Geld verlieren.\n"
            "Starte mit: tradeforge live --i-understand-the-risk"
        )
        raise typer.Exit(code=1)
    settings = load_settings(config)
    settings.mode = "live"
    runner = BotRunner(settings)
    runner.run_loop(iterations=1 if once else None)


@app.command("dashboard")
def dashboard() -> None:
    """Startet das Streamlit-Dashboard."""
    import subprocess
    import sys

    dash = Path(__file__).resolve().parents[2] / "dashboard" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(dash)], check=False)


if __name__ == "__main__":
    app()
