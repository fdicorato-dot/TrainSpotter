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
    entries = [{"score": s, "ticker": f"T{s}"} for s in (70, 95, 80)]
    wl = night_scan.build_watchlist(entries)
    assert [e["score"] for e in wl] == [95, 80, 70]
