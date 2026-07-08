from datetime import date

import pandas as pd
from trainspotter import html_report, night_scan, state, telegram_bot, universe
from trainspotter.data import yahoo
import trainspotter.config as cfg

def build(us_universe, de_universe, fetch_fn, index_fetch_fn,
          names: dict | None = None) -> list[dict]:
    entries = []
    for market, tickers in (("us", us_universe), ("eu", de_universe)):
        index_close = index_fetch_fn(market)
        data = fetch_fn(tickers)
        for t, df in data.items():
            try:
                e = night_scan.platform_score(t, df, index_close, market)
                if e:
                    entries.append(e)
            except Exception:
                continue
    wl = night_scan.build_watchlist(entries)
    names = names or {}
    for e in wl:
        e["name"] = names.get(e["ticker"], e["ticker"])
    return wl

def _index_close(market: str) -> pd.Series:
    h = yahoo.daily_history([cfg.INDEX_SYMBOL[market]], period="2y")
    df = h.get(cfg.INDEX_SYMBOL[market])
    return df["Close"] if df is not None else pd.Series(dtype=float)

def main():
    # Schutzplanke: Ohne Indexdaten fehlt die relative Stärke für ALLE Kandidaten —
    # dann lieber die alte Watchlist behalten und laut warnen als still degradieren.
    idx = {m: _index_close(m) for m in ("us", "eu")}
    fehlend = [m for m, s in idx.items() if s.empty]
    if fehlend:
        telegram_bot.send_message(
            f"⚠️ Scanner fährt blind — Indexdaten fehlen für {', '.join(sorted(fehlend))}. "
            "Watchlist wurde NICHT aktualisiert (gestrige bleibt aktiv).")
        raise SystemExit(1)
    names = universe.load_us_names() | universe.load_de_names()
    wl = build(universe.load_us_universe(), universe.load_de_universe(),
               fetch_fn=yahoo.daily_history, index_fetch_fn=lambda m: idx[m], names=names)
    if not wl:                                  # leere Depesche darf Total-Blindheit nicht verdecken
        telegram_bot.send_message(
            "⚠️ Scanner fährt blind — Nacht-Scan lieferte keine Kandidaten (Datenquelle prüfen).")
    state.save_json("state/watchlist.json", wl)
    html_report.write_report(wl, date.today().isoformat())
    state.commit_and_push(["state/watchlist.json", "docs/reports"],
                          f"state: Watchlist {len(wl)} Titel")

if __name__ == "__main__":
    main()
