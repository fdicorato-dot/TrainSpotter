import pandas as pd
from trainspotter import night_scan

def _df(n=80, vol_last5=2_000_000):
    close = pd.Series([100 + 0.3 * i for i in range(n)])
    return pd.DataFrame({"Open": close - 0.1, "High": close + 1, "Low": close - 1,
                         "Close": close,
                         "Volume": [1_000_000] * (n - 5) + [vol_last5] * 5})

def test_platform_score_kandidat():
    e = night_scan.platform_score("TTT", _df(), pd.Series([100.0] * 80), "us")
    # 25 (Volumen 2x) + 25 (0.6% unter 20T-Hoch) + 20 (Trend) + 20 (RS ~17pp) = 90
    assert e["score"] == 90
    assert e["liste"] == "konservativ"           # ADR ~1.7%
    assert e["breakout_level"] == 124.4          # Hoch von Tag n-2: 100+0.3*78+1
    assert e["avg_volume"] > 0 and len(e["criteria"]) == 4

def test_pennystock_fliegt_raus():
    df = _df()
    df[["Open", "High", "Low", "Close"]] = df[["Open", "High", "Low", "Close"]] / 100.0
    assert night_scan.platform_score("PNY", df, pd.Series([100.0] * 80), "us") is None

def test_zu_wenig_score_fliegt_raus():
    df = _df(vol_last5=1_000_000)                # kein Volumen-Aufbau
    df["Close"] = 100.0                          # kein Trend, weit unterm Hoch? ->
    df["High"] = 130.0                           # 23% unterm 20T-Hoch -> keine Naehe-Punkte
    assert night_scan.platform_score("LAME", df, pd.Series([100.0] * 80), "us") is None

def test_build_watchlist_sortiert_und_kappt():
    entries = [{"score": s, "ticker": f"T{s}", "market": "us", "liste": "spekulativ",
                "avg_volume": 1.0} for s in (70, 95, 80)]
    wl = night_scan.build_watchlist(entries)
    assert [e["score"] for e in wl] == [95, 80, 70]

def test_build_watchlist_quoten_und_volumen_tiebreaker():
    import random
    us = [{"ticker": f"US{i}", "market": "us", "liste": "spekulativ", "score": 65,
           "avg_volume": float(i)} for i in range(200)]
    eu = [{"ticker": f"EU{i}", "market": "eu", "liste": "konservativ", "score": 65,
           "avg_volume": float(i)} for i in range(5)]
    cands = us + eu
    random.Random(1).shuffle(cands)
    wl = night_scan.build_watchlist(cands)
    tickers = {e["ticker"] for e in wl}
    assert len(wl) == 150
    assert all(f"EU{i}" in tickers for i in range(5))          # alle EU-kons ueberleben
    us_sel = [e for e in wl if e["market"] == "us"]
    assert len(us_sel) == 145                                  # 70 Quote + 75 Nachbesetzung
    assert min(e["avg_volume"] for e in us_sel) == 55.0        # hoeheres Volumen bevorzugt
    cands2 = us + eu                                           # keine alphabetische Abhaengigkeit
    random.Random(99).shuffle(cands2)
    assert {e["ticker"] for e in night_scan.build_watchlist(cands2)} == tickers

def test_build_watchlist_leere_eu_wird_von_us_gefuellt():
    us_spek = [{"ticker": f"S{i}", "market": "us", "liste": "spekulativ", "score": 65,
                "avg_volume": float(i)} for i in range(100)]
    us_kons = [{"ticker": f"K{i}", "market": "us", "liste": "konservativ", "score": 60,
                "avg_volume": float(i)} for i in range(100)]
    wl = night_scan.build_watchlist(us_spek + us_kons)
    assert len(wl) == 150                                      # US fuellt freie EU-Plaetze
