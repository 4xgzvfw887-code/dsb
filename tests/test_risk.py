from tradeforge.config import RiskConfig
from tradeforge.models import Side, Signal
from tradeforge.risk.manager import RiskManager


def test_position_sizing_respects_caps():
    risk = RiskManager(RiskConfig(risk_per_trade_pct=1.0, max_position_pct=20.0, stop_loss_pct=2.0), 10_000)
    signal = Signal(Side.BUY, 0.8, "test")
    decision = risk.size_order(signal, price=100.0, equity=10_000)
    assert decision.allowed
    assert decision.quantity * 100 <= 10_000 * 0.20 + 1e-6
    assert decision.stop_loss < 100
    assert decision.take_profit > 100


def test_halt_on_drawdown():
    risk = RiskManager(RiskConfig(max_drawdown_pct=10.0), 10_000)
    risk.update_equity(8_500)
    assert risk.halted
    signal = Signal(Side.BUY, 0.9, "x")
    decision = risk.size_order(signal, 100, 8500)
    assert not decision.allowed
