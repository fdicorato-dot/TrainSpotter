import pytest
from trainspotter import triggers

ENTRY = {"ticker": "NVDA", "market": "us", "liste": "spekulativ", "score": 90,
         "breakout_level": 100.0, "adr_pct": 4.0, "avg_volume": 1_000_000,
         "criteria": ["volumen_aufbau:2.0x"]}

def _check(price, vol=600_000, idx=-0.5, entry=ENTRY):
    return triggers.check_trigger(entry, price, vol, idx, 0.3, "2026-07-08")

def test_alert_mit_stop_und_ziel():
    r = _check(101.5)
    assert r["status"] == "alert" and r["id"] == "NVDA-2026-07-08"
    assert r["vol_ratio"] == pytest.approx(2.0)          # 600k / (1M * 0.3)
    assert r["stop"] == pytest.approx(94.0)              # 100 * (1 - 6%)
    assert r["target1"] == pytest.approx(111.65)         # 101.5 * 1.10
    assert r["warning"] is None

def test_kein_ausbruch_kein_alert():
    assert _check(99.5) is None

def test_ohne_volumen_geisterzug():
    assert _check(101.5, vol=250_000) is None            # Ratio 0.83 < 2.0

def test_zug_verpasst():
    assert _check(107.0)["status"] == "missed"           # +7% > 6%-Grenze spek.

def test_marktfilter():
    kons = ENTRY | {"liste": "konservativ", "adr_pct": 2.0}
    assert triggers.check_trigger(kons, 101.5, 600_000, -2.0, 0.3, "2026-07-08") is None
    r = _check(101.5, idx=-2.0)                          # spekulativ: Warnung statt Blockade
    assert "Gegenwind" in r["warning"]

def test_alert_disziplin():
    cands = [dict(ENTRY, breakout_level=100.0) | {"id": f"T{i}-d", "status": "alert",
             "score": 60 + i, "liste": "spekulativ"} for i in range(7)]
    out = triggers.apply_alert_discipline(cands, alerts_sent={"T6-d"}, sent_counts={"spekulativ": 2})
    ids = [c["id"] for c in out]
    assert "T6-d" not in ids                             # schon gesendet
    assert len(ids) == 3                                 # 5 Budget - 2 verbraucht
    assert ids == ["T5-d", "T4-d", "T3-d"]               # beste Scores zuerst
