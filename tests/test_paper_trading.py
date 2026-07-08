import pytest
from trainspotter import paper_trading as pt

ALERT = {"id": "NVDA-2026-07-08", "ticker": "NVDA", "market": "us", "liste": "spekulativ",
         "score": 90, "status": "alert", "price": 100.0, "entry": 100.0,
         "stop": 94.0, "target1": 110.0, "breakout_level": 100.0, "vol_ratio": 2.5,
         "dist_pct": 1.0, "reasons": ["r1"], "warning": None}

def test_open_mit_slippage():
    pos = pt.open_position(ALERT, "2026-07-08T16:00:00+00:00")
    # spekulativ: 0.75% Slippage -> 100 * 1.0075 = 100.75
    assert pos["entry"] == pytest.approx(100.75)
    assert pos["qty"] == pytest.approx(1000.0 / 100.75)

def test_stop_schliesst_alles():
    pos = pt.open_position(ALERT, "2026-07-08T16:00:00+00:00")
    events, trade = pt.update_position(pos, 93.5, "2026-07-08T16:30:00+00:00")
    assert events == ["stop"] and trade["reason"] == "stop"
    # trade["pnl_eur"] ist auf 2 Stellen gerundet -> abs-Toleranz noetig
    assert float(trade["pnl_eur"]) == pytest.approx((1000.0 / 100.75) * (93.5 - 100.75), abs=0.01)

def test_ziel1_bucht_haelfte_und_trailt():
    pos = pt.open_position(ALERT, "2026-07-08T16:00:00+00:00")
    events, trade = pt.update_position(pos, 110.5, "2026-07-08T17:00:00+00:00")
    assert "target1" in events and trade is None
    assert pos["half_booked"] and pos["qty"] == pytest.approx(1000.0 / 100.75 / 2)
    assert pos["realized"] == pytest.approx((1000.0 / 100.75 / 2) * (110.0 - 100.75))
    assert pos["stop"] == pytest.approx(110.5 * 0.995)   # Trailing unterm 30-Min-Tief
    # naechster Tick faellt unter den Trail -> Rest zu, Gesamt-PnL = realisiert + Rest
    events2, trade2 = pt.update_position(pos, 109.0, "2026-07-08T17:02:00+00:00")
    assert events2 == ["stop"] and trade2["reason"] == "trail_stop"

def test_session_close_spekulativ():
    pos = pt.open_position(ALERT, "2026-07-08T16:00:00+00:00")
    events, trade = pt.update_position(pos, 103.0, "2026-07-08T20:00:00+00:00", session_close=True)
    assert trade["reason"] == "tagesschluss"

def test_session_close_konservativ_haelt_3_tage():
    pos = pt.open_position(dict(ALERT, liste="konservativ"), "2026-07-08T10:00:00+00:00")
    for day in (8, 9):
        _, trade = pt.update_position(pos, 101.0, f"2026-07-{day:02d}T15:30:00+00:00", session_close=True)
        assert trade is None
    _, trade = pt.update_position(pos, 101.0, "2026-07-10T15:30:00+00:00", session_close=True)
    assert trade["reason"] == "max_haltedauer"
