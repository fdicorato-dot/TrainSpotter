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

def test_criteria_klartext_uebersetzt_alle_kuerzel():
    assert reports.criteria_klartext(
        ["volumen_aufbau:2.0x", "nahe_ausbruch:-0.4%", "trend_intakt", "rel_staerke:+17pp"]
    ) == "Vol 2.0× · 0.4% unterm Hoch · Trend ✓ · RS +17pp"
    assert reports.criteria_klartext(["nahe_ausbruch:+0.2%"]) == "0.2% überm Hoch"
    assert reports.criteria_klartext(["ausbruch_ueber:15.43"]) == "Ausbruch über 15.43"
    assert reports.criteria_klartext(["volumen:2.5x_zeitanteilig"]) == "Vol 2.5× (zeitanteilig)"
    assert reports.criteria_klartext(["tages_topmover"]) == "Tages-Topmover"
    assert reports.criteria_klartext(["voellig_unbekannt:9"]) == "voellig_unbekannt:9"

def test_depesche_heartbeat_leer():
    assert "keine Kandidaten" in reports.format_depesche([])

def _wl_entry(i, ticker, market="us", name=None):
    return {"ticker": ticker, "name": name or ticker, "liste": "spekulativ",
            "breakout_level": 100.0 + i, "score": 90 - i, "market": market,
            "criteria": ["volumen_aufbau:2.0x", "trend_intakt"]}

def test_depesche_top10_mit_klarnamen_und_link():
    wl = [_wl_entry(0, "NVDA", name="NVIDIA Corporation")]
    wl += [_wl_entry(i, f"T{i}") for i in range(1, 12)]
    d = reports.format_depesche(wl, report_url="https://example.org/reports/2026-07-08.html")
    assert d.startswith("📋 Morgen-Depesche · ")
    assert "Top 10 von 12 Zügen am Bahnsteig:" in d
    assert "1. 🇺🇸 NVDA — NVIDIA Corporation [spekulativ]" in d
    assert "Ausbruch über 100.00 · Score 90" in d
    assert "Vol 2.0× · Trend ✓" in d
    assert "T11" not in d                                   # nur Top 10
    assert "📄 Vollanalyse (12 Titel, Prüf-Links, Methodik):" in d
    assert "https://example.org/reports/2026-07-08.html" in d
    assert len(d) < 4000

def test_depesche_eu_flagge_und_ohne_url_kein_footer():
    d = reports.format_depesche([_wl_entry(0, "SAP.DE", market="eu", name="SAP")])
    assert "1. 🇩🇪 SAP.DE — SAP [spekulativ]" in d
    assert "Vollanalyse" not in d

def test_bilanz_hat_disclaimer():
    assert cfg.DISCLAIMER in reports.format_bilanz(reports.compute_stats(TRADES), [], [])
