from tradeforge.backtest.engine import run_backtest
from tradeforge.config import load_settings
from tradeforge.data.feed import generate_synthetic_ohlcv


def test_backtest_runs_on_synthetic_data():
    settings = load_settings()
    settings.ml.enabled = True
    settings.strategy.name = "ensemble"
    settings.initial_capital = 10_000
    df = generate_synthetic_ohlcv(bars=300, seed=7)
    result = run_backtest(df, settings)
    assert result.report.final_equity > 0
    assert len(result.equity_curve) > 0
    assert result.report.trades >= 0
