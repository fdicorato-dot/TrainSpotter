import pandas as pd
import importlib
run_night_scan = importlib.import_module("scripts.run_night_scan")

def _df(n=80):
    close = pd.Series([100 + 0.3 * i for i in range(n)])
    return pd.DataFrame({"Open": close - 0.1, "High": close + 1, "Low": close - 1,
                         "Close": close, "Volume": [1_000_000] * (n - 5) + [2_000_000] * 5})

def test_build_findet_kandidaten_und_markiert_markt():
    data = {"TTT": _df()}
    wl = run_night_scan.build(["TTT"], ["SAP.DE"],
                              fetch_fn=lambda ts: {t: _df() for t in ts if t == "TTT"},
                              index_fetch_fn=lambda m: pd.Series([100.0] * 80))
    assert len(wl) == 1 and wl[0]["ticker"] == "TTT" and wl[0]["market"] == "us"
    assert wl[0]["name"] == "TTT"                        # ohne names-Dict: Ticker-Fallback

def test_build_reichert_klarnamen_an():
    wl = run_night_scan.build(["TTT"], [],
                              fetch_fn=lambda ts: {t: _df() for t in ts if t == "TTT"},
                              index_fetch_fn=lambda m: pd.Series([100.0] * 80),
                              names={"TTT": "Test Trains Inc."})
    assert wl[0]["name"] == "Test Trains Inc."


def test_main_bricht_ohne_indexdaten_ab(monkeypatch):
    import pandas as pd
    warnungen, gespeichert = [], []
    monkeypatch.setattr(run_night_scan, "_index_close", lambda m: pd.Series(dtype=float))
    monkeypatch.setattr(run_night_scan.telegram_bot, "send_message",
                        lambda t: warnungen.append(t) or True)
    monkeypatch.setattr(run_night_scan.state, "save_json",
                        lambda p, d: gespeichert.append(p))
    try:
        run_night_scan.main()
        assert False, "SystemExit erwartet"
    except SystemExit as e:
        assert e.code == 1
    assert warnungen and "Indexdaten fehlen" in warnungen[0]
    assert gespeichert == []          # alte Watchlist bleibt unangetastet
