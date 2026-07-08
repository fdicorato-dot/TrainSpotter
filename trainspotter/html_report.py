"""Täglicher HTML-Report: komplette Watchlist mit Prüf-Links und Methodik.

Self-contained (Inline-CSS, kein JS, keine externen Ressourcen), mobil lesbar,
ausgeliefert über GitHub Pages aus docs/reports/. Beantwortet: "Auf welchen
Daten basiert die These? Wie kann ich das prüfen?"
"""
import html as _h
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import trainspotter.config as cfg
from trainspotter.reports import criteria_klartext

_FLAGS = {"us": "🇺🇸", "eu": "🇩🇪"}
_DOCS_URL = "https://github.com/fdicorato-dot/TrainSpotter/tree/main/docs"

_CSS = """
body { font-family: system-ui, -apple-system, sans-serif; margin: 0 auto;
       max-width: 720px; padding: 16px; line-height: 1.5; color: #1a1a1a; }
h1 { font-size: 1.3rem; } h2 { font-size: 1.1rem; margin-top: 2rem; }
.card { border: 1px solid #ccc; border-radius: 8px; padding: 12px; margin: 12px 0; }
.card h3 { margin: 0 0 6px; font-size: 1rem; }
.badge { display: inline-block; font-size: 0.75rem; padding: 2px 8px;
         border-radius: 10px; background: #eef; color: #225; margin-left: 6px; }
.badge.spekulativ { background: #fee; color: #822; }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
td, th { padding: 4px 8px; text-align: left; border-bottom: 1px solid #eee; }
.card td:first-child { color: #555; white-space: nowrap; }
.scroll { overflow-x: auto; }
.muted { color: #666; font-size: 0.85rem; }
a { color: #0645ad; }
footer { margin-top: 2rem; border-top: 1px solid #ccc; padding-top: 8px; }
"""


def _fmt_volume(v: float) -> str:
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}".replace(".", ",") + " Mio Stk"
    if v >= 1_000:
        return f"{v / 1_000:.0f} Tsd Stk"
    return f"{v:.0f} Stk"


def _pruef_links(ticker: str, market: str) -> str:
    tv = f"XETR-{ticker[:-3]}" if market == "eu" else ticker
    return (f'<a href="https://finance.yahoo.com/quote/{_h.escape(ticker)}">Yahoo</a> · '
            f'<a href="https://www.tradingview.com/symbols/{_h.escape(tv)}/">TradingView</a>')


def _card(e: dict) -> str:
    t, name = _h.escape(e["ticker"]), _h.escape(e.get("name", e["ticker"]))
    flag, liste = _FLAGS.get(e["market"], ""), _h.escape(e["liste"])
    rows = [("Ausbruchsniveau", f"{e['breakout_level']:.2f}"),
            ("Score", str(e["score"])),
            ("ADR (Ø-Tagesspanne)", f"{e.get('adr_pct', 0):.1f} %"),
            ("Ø-Volumen", _fmt_volume(e.get("avg_volume", 0))),
            ("Kriterien", _h.escape(criteria_klartext(e.get("criteria", []))))]
    trs = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
    return (f'<div class="card"><h3>{flag} {t} — {name}'
            f'<span class="badge {liste}">{liste}</span></h3>'
            f'<table>{trs}</table>'
            f'<p class="muted">Selbst prüfen: {_pruef_links(e["ticker"], e["market"])}</p></div>')


def _summary(watchlist: list[dict]) -> str:
    teile = []
    for market in ("us", "eu"):
        counts = {l: sum(1 for e in watchlist if e["market"] == market and e["liste"] == l)
                  for l in cfg.LISTEN}
        if sum(counts.values()):
            teile.append(f"{_FLAGS[market]} " +
                         " / ".join(f"{n} {l}" for l, n in counts.items() if n))
    return f"{len(watchlist)} Titel" + ("".join(f" · {t}" for t in teile))


def _methodik() -> str:
    return f"""
<h2>Worauf basiert die These?</h2>
<p>Datenbasis: 2 Jahre Tageskurse (Yahoo Finance) für ~7000 US- und 50 DE-Titel,
nächtlicher Scan. Jeder Titel wird gegen 5 Kriterien geprüft:</p>
<ul>
<li>Volumen-Aufbau ≥{cfg.VOL_BUILDUP_RATIO}× (letzte {cfg.RECENT_VOL_DAYS} Tage vs.
{cfg.BASELINE_VOL_DAYS}-Tage-Basis) — 25 Punkte</li>
<li>Max. {cfg.NEAR_BREAKOUT_PCT}% unter dem Widerstand ({cfg.BREAKOUT_WINDOW}-Tage-Hoch) — 25 Punkte</li>
<li>Trend intakt: Kurs &gt; SMA20 &gt; SMA50 — 20 Punkte</li>
<li>Relative Stärke vs. Index ({cfg.RS_DAYS} Tage): &gt;5pp — 20 Punkte, &gt;0 — 10 Punkte</li>
<li>Mindest-Score für die Watchlist: {cfg.SCORE_MIN} Punkte</li>
</ul>
<p>Listen-Einteilung per Ø-Tagesspanne (ADR): ≥{cfg.ADR_MIN_SPEC}% spekulativ,
≥{cfg.ADR_MIN_KONS}% konservativ. Die Watchlist ist per Quote auf Markt und Liste
verteilt (max. {cfg.WATCHLIST_SIZE} Titel).</p>
<p>Spezifikation und Research: <a href="{_DOCS_URL}">GitHub-Repo, docs/</a></p>
"""


def _gesamt_tabelle(watchlist: list[dict]) -> str:
    trs = "".join(
        f"<tr><td>{_h.escape(e['ticker'])}</td><td>{_h.escape(e.get('name', e['ticker']))}</td>"
        f"<td>{_FLAGS.get(e['market'], '')}</td><td>{_h.escape(e['liste'])}</td>"
        f"<td>{e['score']}</td><td>{e['breakout_level']:.2f}</td>"
        f"<td>{e.get('adr_pct', 0):.1f}</td></tr>"
        for e in watchlist)
    return (f'<h2>Alle {len(watchlist)} Kandidaten</h2><div class="scroll"><table>'
            "<tr><th>Ticker</th><th>Name</th><th>Markt</th><th>Liste</th>"
            "<th>Score</th><th>Ausbruch</th><th>ADR%</th></tr>"
            f"{trs}</table></div>")


def build_report(watchlist: list[dict], datum_iso: str) -> str:
    y, m, d = datum_iso.split("-")
    stand = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y %H:%M")
    cards = "".join(_card(e) for e in watchlist[:10])
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TrainSpotter Tagesreport {d}.{m}.{y}</title>
<style>{_CSS}</style>
</head>
<body>
<h1>🚂 TrainSpotter — Tagesreport {d}.{m}.{y}</h1>
<p class="muted">{_summary(watchlist)}</p>
<h2>Top 10 im Detail</h2>
{cards or '<p>Keine Kandidaten.</p>'}
{_methodik()}
{_gesamt_tabelle(watchlist)}
<footer class="muted">Erstellt {stand} · {_h.escape(cfg.DISCLAIMER)}</footer>
</body>
</html>
"""


def write_report(watchlist: list[dict], datum_iso: str) -> str:
    """Schreibt den Tagesreport und aktualisiert index.html (Redirect auf den neuesten)."""
    d = Path("docs/reports")
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{datum_iso}.html"
    path.write_text(build_report(watchlist, datum_iso), encoding="utf-8")
    newest = max(p.name for p in d.glob("*.html") if p.name != "index.html")
    (d / "index.html").write_text(
        f'<!DOCTYPE html>\n<html lang="de"><head><meta charset="utf-8">\n'
        f'<meta http-equiv="refresh" content="0; url={newest}"></head>\n'
        f'<body><a href="{newest}">Zum neuesten Report</a></body></html>\n',
        encoding="utf-8")
    return str(path)
