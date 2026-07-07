from datetime import datetime, timezone
from trainspotter import live_observer as obs

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
    assert "TTT-2026-07-08" in ctx["alerts_sent"]["2026-07-08"]
    assert events

def test_missed_meldet_und_persistiert_ohne_position(tmp_path):
    deps, sent = _deps(108.0)                     # dist 8% > 6% -> missed (spekulativ)
    ctx = _ctx(tmp_path)
    events = obs.run_cycle(ctx, deps)
    assert any("ZUG VERPASST" in m for m in sent)
    assert ctx["positions"] == []
    assert "TTT-2026-07-08" in ctx["alerts_sent"]["2026-07-08"]
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
