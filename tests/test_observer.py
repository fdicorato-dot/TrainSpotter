from datetime import datetime, timezone
from trainspotter import live_observer as obs, state

ENTRY = {"ticker": "TTT", "market": "us", "liste": "spekulativ", "score": 90,
         "breakout_level": 100.0, "adr_pct": 4.0, "avg_volume": 1_000_000,
         "criteria": ["volumen_aufbau:2.0x"]}

# 16:00 UTC = 2,5h von 6,5h US-Sitzung -> elapsed 0.385; 900k Volumen -> Ratio 2.34 >= 2.0
def _deps(price, vol=900_000):
    sent = []
    return obs.Deps(quotes_fn=lambda ts: {"TTT": {"price": price, "day_volume": vol}},
                    index_fn=lambda: -0.5, send_fn=lambda t: sent.append(t) or True,
                    review_fn=lambda a: None,
                    now_fn=lambda: datetime(2026, 7, 8, 16, 0, tzinfo=timezone.utc)), sent

def _ctx(tmp_path):
    return {"market": "us", "watchlist": [ENTRY], "positions": [],
            "alerts_sent": {"2026-07-08": []}, "today": "2026-07-08",
            "trades_path": str(tmp_path / "trades.csv")}

def test_zyklus_erzeugt_alert_und_position(tmp_path):
    deps, sent = _deps(101.5)
    ctx = _ctx(tmp_path)
    events = obs.run_cycle(ctx, deps)
    assert any("ZUG ERKANNT" in m for m in sent)
    assert len(ctx["positions"]) == 1
    assert "TTT-2026-07-08" in [r["id"] for r in ctx["alerts_sent"]["2026-07-08"]]
    assert events

def test_missed_meldet_und_persistiert_ohne_position(tmp_path):
    deps, sent = _deps(108.0)                     # dist 8% > 6% -> missed (spekulativ)
    ctx = _ctx(tmp_path)
    events = obs.run_cycle(ctx, deps)
    assert any("ZUG VERPASST" in m for m in sent)
    assert ctx["positions"] == []
    assert "TTT-2026-07-08" in [r["id"] for r in ctx["alerts_sent"]["2026-07-08"]]
    assert "missed:TTT-2026-07-08" in events

def test_kein_doppelalert_im_naechsten_zyklus(tmp_path):
    deps, sent = _deps(101.5)
    ctx = _ctx(tmp_path)
    obs.run_cycle(ctx, deps)
    n = len(sent)
    obs.run_cycle(ctx, deps)
    assert len(ctx["positions"]) == 1           # nicht doppelt eroeffnet
    assert len([m for m in sent[n:] if "ZUG ERKANNT" in m]) == 0

def test_stop_schliesst_position_und_meldet(tmp_path):
    deps, sent = _deps(101.5)
    ctx = _ctx(tmp_path)
    obs.run_cycle(ctx, deps)
    deps2, sent2 = _deps(90.0)
    events = obs.run_cycle(ctx, deps2)
    assert ctx["positions"] == []
    assert any("geschlossen" in m for m in sent2)

def test_movers_entries_erzeugt_adhoc_eintraege():
    import pandas as pd
    close = pd.Series([100 + 0.3 * i for i in range(80)])
    df = pd.DataFrame({"Open": close - 0.1, "High": close + 1, "Low": close - 1,
                       "Close": close, "Volume": [1_000_000] * 80})
    entries = obs.movers_entries(["MOV"], lambda ts: {"MOV": df}, "us",
                                 known={"TTT"})
    assert entries[0]["ticker"] == "MOV" and entries[0]["criteria"] == ["tages_topmover"]
    assert obs.movers_entries(["TTT"], lambda ts: {}, "us", known={"TTT"}) == []

def test_sent_counts_zaehlt_nur_eigene_alerts():
    ctx = {"market": "us", "watchlist": [], "today": "2026-07-08",
           "alerts_sent": {"2026-07-08": [
               {"id": "A-2026-07-08", "liste": "spekulativ", "status": "alert"},
               {"id": "B-2026-07-08", "liste": "spekulativ", "status": "missed"},
               {"id": "C-2026-07-08", "liste": "konservativ", "status": "alert"}]}}
    counts = obs._sent_counts(ctx)
    assert counts["spekulativ"] == 1        # nur der Alert, nicht der Missed
    assert counts["konservativ"] == 1

def _pos(ticker, liste, opened, trails):
    return {"id": f"{ticker}-2026-07-07", "ticker": ticker, "market": "us", "liste": liste,
            "score": 90, "criteria": "x", "entry": 100.0, "qty": 10.0, "stop": 94.0,
            "target1": 110.0, "half_booked": False, "realized": 0.0,
            "trail_prices": trails, "opened": opened, "open_days": 1}

def test_uebernacht_spekulativ_wird_notgeschlossen(tmp_path):
    trades_path = str(tmp_path / "trades.csv")
    sent = []
    positions = [_pos("OLD", "spekulativ", "2026-07-07T15:00:00+00:00",
                      [["2026-07-07T19:00:00+00:00", 105.0]]),
                 _pos("KON", "konservativ", "2026-07-07T15:00:00+00:00", [])]
    kept = obs.recover_overnight(positions, "2026-07-08", trades_path,
                                 lambda m: sent.append(m) or True)
    assert [p["ticker"] for p in kept] == ["KON"]          # konservativ bleibt offen
    rows = state.load_trades(trades_path)
    assert len(rows) == 1 and rows[0]["reason"] == "notschluss_uebernacht"
    assert rows[0]["exit"] == "105.0"                       # letzter Trail-Preis
    assert any("notgeschlossen" in m for m in sent)

def _deps_at(price, time_iso, ticker="TR"):
    sent = []
    return obs.Deps(quotes_fn=lambda ts, p=price: {ticker: {"price": p, "day_volume": 1_000_000}},
                    index_fn=lambda: 0.5, send_fn=lambda t: sent.append(t) or True,
                    review_fn=lambda a: None,
                    now_fn=lambda ti=time_iso: datetime.fromisoformat(ti)), sent

def test_trail_meldung_gedrosselt(tmp_path):
    pos = {"id": "TR-2026-07-08", "ticker": "TR", "market": "us", "liste": "konservativ",
           "score": 90, "criteria": "x", "entry": 100.0, "qty": 5.0, "stop": 100.0,
           "target1": 50.0, "half_booked": True, "realized": 10.0, "trail_prices": [],
           "opened": "2026-07-08T14:00:00+00:00", "open_days": 0, "last_notified_stop": 100.0}
    ctx = {"market": "us", "watchlist": [], "positions": [pos], "today": "2026-07-08",
           "alerts_sent": {"2026-07-08": []}, "trades_path": str(tmp_path / "t.csv")}
    d1, s1 = _deps_at(100.7, "2026-07-08T15:00:00+00:00")   # +0.20% -> gedrosselt
    obs.run_cycle(ctx, d1)
    d2, s2 = _deps_at(100.9, "2026-07-08T15:40:00+00:00")   # +0.20% -> gedrosselt
    obs.run_cycle(ctx, d2)
    assert [m for m in s1 + s2 if "nachgezogen" in m] == []
    d3, s3 = _deps_at(105.0, "2026-07-08T16:30:00+00:00")   # grosser Sprung -> Meldung
    obs.run_cycle(ctx, d3)
    assert len([m for m in s3 if "nachgezogen" in m]) == 1

def test_session_close_eroeffnet_keine_alerts(tmp_path):
    deps, sent = _deps(101.5)                               # loest sonst einen Alert aus
    ctx = _ctx(tmp_path)
    events = obs.run_cycle(ctx, deps, session_close=True)
    assert ctx["positions"] == []
    assert not any("ZUG ERKANNT" in m for m in sent)
    assert not any(e.startswith("alert:") for e in events)
