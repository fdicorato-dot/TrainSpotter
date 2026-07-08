from datetime import datetime
from zoneinfo import ZoneInfo

import trainspotter.config as cfg

def compute_stats(trades: list[dict]) -> dict:
    out = {}
    for liste in cfg.LISTEN:
        pnls = [float(t["pnl_eur"]) for t in trades if t["liste"] == liste]
        wins = [p for p in pnls if p >= 0]
        losses = [p for p in pnls if p < 0]
        out[liste] = {"n": len(pnls),
                      "hit_rate": round(len(wins) / len(pnls) * 100, 1) if pnls else 0.0,
                      "avg_win": round(sum(wins) / len(wins), 2) if wins else 0.0,
                      "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0.0,
                      "profit_factor": round(sum(wins) / abs(sum(losses)), 2) if losses else 0.0,
                      "total_eur": round(sum(pnls), 2)}
    return out

def criteria_klartext(criteria: list[str]) -> str:
    """Übersetzt Scan-Kürzel in lesbare Kurzform, unbekannte bleiben wörtlich."""
    out = []
    for c in criteria:
        key, _, val = c.partition(":")
        if key == "volumen_aufbau" and val:
            out.append(f"Vol {val.rstrip('x')}×")
        elif key == "nahe_ausbruch" and val:
            richtung = "unterm" if val.startswith("-") else "überm"
            out.append(f"{val.lstrip('+-')} {richtung} Hoch")
        elif c == "trend_intakt":
            out.append("Trend ✓")
        elif key == "rel_staerke" and val:
            out.append(f"RS {val}")
        elif key == "ausbruch_ueber" and val:
            out.append(f"Ausbruch über {val}")
        elif key == "volumen" and val.endswith("_zeitanteilig"):
            out.append(f"Vol {val.removesuffix('_zeitanteilig').rstrip('x')}× (zeitanteilig)")
        elif c == "tages_topmover":
            out.append("Tages-Topmover")
        else:
            out.append(c)
    return " · ".join(out)

_WOCHENTAGE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
_FLAGS = {"us": "🇺🇸", "eu": "🇩🇪"}

def format_depesche(watchlist: list[dict], report_url: str | None = None) -> str:
    if not watchlist:
        return "📋 Morgen-Depesche: heute keine Kandidaten am Bahnsteig. (System läuft.)"
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    lines = [f"📋 Morgen-Depesche · {_WOCHENTAGE[now.weekday()]} {now:%d.%m.}",
             f"Top 10 von {len(watchlist)} Zügen am Bahnsteig:"]
    for i, e in enumerate(watchlist[:10], 1):
        name = e.get("name", e["ticker"])
        lines += ["",
                  f"{i}. {_FLAGS.get(e['market'], '')} {e['ticker']} — {name} [{e['liste']}]",
                  f"   Ausbruch über {e['breakout_level']:.2f} · Score {e['score']}",
                  f"   {criteria_klartext(e.get('criteria', []))}"]
    if report_url:
        lines += ["", f"📄 Vollanalyse ({len(watchlist)} Titel, Prüf-Links, Methodik):",
                  report_url]
    return "\n".join(lines)

def _stats_lines(stats: dict) -> list[str]:
    return [f"{l}: {s['n']} Trades, Treffer {s['hit_rate']}%, "
            f"PF {s['profit_factor']}, Summe {s['total_eur']:+.2f} €"
            for l, s in stats.items()]

def format_bilanz(stats: dict, open_positions: list[dict], today_trades: list[dict]) -> str:
    lines = ["📊 Abend-Bilanz"]
    day = sum(float(t["pnl_eur"]) for t in today_trades)
    lines.append(f"Heute geschlossen: {len(today_trades)} Trades, {day:+.2f} €")
    lines += [f"Offen: {p['ticker']} [{p['liste'][:4]}] Stop {p['stop']:.2f}"
              for p in open_positions] or ["Offen: keine Positionen"]
    lines += ["Gesamt:"] + _stats_lines(stats) + [cfg.DISCLAIMER]
    return "\n".join(lines)

def format_stats_command(stats: dict) -> str:
    return "\n".join(["📊 Gesamtstatistik:"] + _stats_lines(stats))

def format_status_command(open_positions: list[dict], today_alert_ids: list[str]) -> str:
    lines = [f"Offen: {p['ticker']} Einstieg {p['entry']:.2f} Stop {p['stop']:.2f}"
             for p in open_positions] or ["Keine offenen Positionen."]
    lines.append(f"Alerts heute: {', '.join(today_alert_ids) or 'keine'}")
    return "\n".join(lines)
