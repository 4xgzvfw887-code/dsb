from tradeforge.exchange.paper import PaperBroker
from tradeforge.models import Side


def test_paper_roundtrip_long():
    broker = PaperBroker(cash=10_000, fee_rate=0.001, slippage_pct=0.0)
    trade = broker.open_position(Side.BUY, 1.0, 100.0, 95.0, 110.0, "entry")
    assert trade is not None
    assert trade.status.value == "filled"
    assert broker.cash < 10_000
    pos = broker.positions[0]
    exit_trade = broker.close_position(pos, 110.0, "tp")
    assert exit_trade.pnl > 0
    assert len(broker.positions) == 0
