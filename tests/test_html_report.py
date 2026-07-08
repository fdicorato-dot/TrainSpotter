import trainspotter.config as cfg
from trainspotter import html_report

ENTRIES = [
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "market": "us", "liste": "spekulativ",
     "score": 90, "breakout_level": 100.0, "adr_pct": 4.2, "avg_volume": 1_300_000.0,
     "criteria": ["volumen_aufbau:2.0x", "trend_intakt"]},
    {"ticker": "SAP.DE", "name": "SAP", "market": "eu", "liste": "konservativ",
     "score": 75, "breakout_level": 215.5, "adr_pct": 1.8, "avg_volume": 800_000.0,
     "criteria": ["nahe_ausbruch:-0.4%", "rel_staerke:+5pp"]},
]


def test_build_report_smoke():
    html = html_report.build_report(ENTRIES, "2026-07-08")
    assert html.startswith("<!DOCTYPE html>")
    assert '<html lang="de">' in html and 'charset' in html and "viewport" in html
    assert "NVDA" in html and "NVIDIA Corporation" in html
    assert "SAP.DE" in html and "SAP" in html
    assert "https://finance.yahoo.com/quote/NVDA" in html
    assert "https://www.tradingview.com/symbols/XETR-SAP/" in html
    assert "https://www.tradingview.com/symbols/NVDA/" in html
    assert "Worauf basiert die These?" in html
    assert f"{cfg.VOL_BUILDUP_RATIO}" in html and f"{cfg.SCORE_MIN}" in html
    assert cfg.DISCLAIMER in html
    assert "08.07.2026" in html
    assert "1,3 Mio Stk" in html
    assert "Vol 2.0× · Trend ✓" in html
    body = html.split("</style>")[-1]                      # CSS hat legitime Klammern
    assert "{" not in body and "}" not in body             # keine Template-Reste


def test_build_report_escaped_und_leer():
    entry = ENTRIES[0] | {"name": "A & B <Corp>"}
    html = html_report.build_report([entry], "2026-07-08")
    assert "A &amp; B &lt;Corp&gt;" in html
    assert "<Corp>" not in html
    leer = html_report.build_report([], "2026-07-08")
    assert "0 Titel" in leer


def test_write_report_erzeugt_datei_und_index(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = html_report.write_report(ENTRIES, "2026-07-08")
    assert path == "docs/reports/2026-07-08.html"
    assert (tmp_path / path).exists()
    index = (tmp_path / "docs/reports/index.html").read_text()
    assert "2026-07-08.html" in index and "refresh" in index
