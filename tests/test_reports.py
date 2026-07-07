import pytest
import trainspotter.config as cfg
from trainspotter import reports

TRADES = [{"liste": "konservativ", "pnl_eur": "50.0"},
          {"liste": "konservativ", "pnl_eur": "-20.0"},
          {"liste": "konservativ", "pnl_eur": "30.0"}]

def test_compute_stats():
    s = reports.compute_stats(TRADES)["konservativ"]
    assert s["n"] == 3
    assert s["hit_rate"] == pytest.approx(66.7, abs=0.1)
    assert s["profit_factor"] == pytest.approx(4.0)      # 80 Gewinn / 20 Verlust
    assert s["total_eur"] == pytest.approx(60.0)

def test_depesche_heartbeat_leer():
    assert "keine Kandidaten" in reports.format_depesche([])

def test_depesche_mit_eintraegen():
    wl = [{"ticker": "NVDA", "liste": "spekulativ", "breakout_level": 100.0, "score": 90, "market": "us"}]
    d = reports.format_depesche(wl)
    assert "NVDA" in d and "100.00" in d and "1 Züge" in d

def test_bilanz_hat_disclaimer():
    assert cfg.DISCLAIMER in reports.format_bilanz(reports.compute_stats(TRADES), [], [])
