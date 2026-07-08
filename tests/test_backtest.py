import pandas as pd
import pytest
from trainspotter import backtest

ENTRY = {"ticker": "TTT", "market": "us", "liste": "konservativ", "score": 90,
         "breakout_level": 100.0, "adr_pct": 2.0, "avg_volume": 1_000_000, "criteria": []}

def _day(o, h, l, c):
    return {"Open": o, "High": h, "Low": l, "Close": c, "Volume": 1_000_000}

def test_stop_am_ersten_tag():
    df = pd.DataFrame([_day(99, 101, 96, 97)])           # bricht aus, faellt auf Stop 97.0
    t = backtest.simulate_trade(ENTRY, df, 0)
    assert t["reason"] == "stop"
    # Einstieg max(100, 99)*1.002 = 100.2; Stop 100*0.97 = 97 -> -3.19%
    assert t["pnl_pct"] == pytest.approx((97.0 / 100.2 - 1) * 100, abs=0.01)

def test_ziel1_und_zeitausstieg():
    df = pd.DataFrame([_day(99, 106, 99, 105),           # Einstieg 100.2, Ziel1 104.208 erreicht
                       _day(105, 107, 104, 106),
                       _day(106, 108, 105, 107)])        # Zeitausstieg Tag 3 zu 107
    t = backtest.simulate_trade(ENTRY, df, 0)
    assert t["reason"] == "zeitausstieg"
    halb_ziel = (104.208 / 100.2 - 1) * 100 / 2
    halb_rest = (107.0 / 100.2 - 1) * 100 / 2
    assert t["pnl_pct"] == pytest.approx(halb_ziel + halb_rest, abs=0.05)

def test_gap_drueber_kein_trade():
    df = pd.DataFrame([_day(105, 106, 104, 105)])        # Open 5% ueber Level -> kein Einstieg
    assert backtest.simulate_trade(ENTRY, df, 0) is None

def test_backtest_ueberspringt_unaligned():
    n = 65
    close = pd.Series([100 + 0.3 * i for i in range(n)])
    df_ok = pd.DataFrame({"Open": close - 0.1, "High": close + 1, "Low": close - 1,
                          "Close": close, "Volume": [1_000_000] * n})
    df_short = df_ok.iloc[:60].copy()                    # kuerzer -> Index-Versatz
    index_close = pd.Series([100.0] * n)
    res = backtest.simulate({"AAA": df_ok, "BBB": df_short}, index_close, "us", start_idx=60)
    assert res.attrs["skipped"] == 1                     # nur BBB uebersprungen
    if not res.empty:
        assert set(res["ticker"].unique()) == {"AAA"}    # BBB nie simuliert
