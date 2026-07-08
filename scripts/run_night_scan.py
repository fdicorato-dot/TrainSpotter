import pandas as pd
from trainspotter import night_scan, state, telegram_bot, universe
from trainspotter.data import yahoo
import trainspotter.config as cfg

def build(us_universe, de_universe, fetch_fn, index_fetch_fn) -> list[dict]:
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
    return night_scan.build_watchlist(entries)

def _index_close(market: str) -> pd.Series:
    h = yahoo.daily_history([cfg.INDEX_SYMBOL[market]], period="2y")
    df = h.get(cfg.INDEX_SYMBOL[market])
    return df["Close"] if df is not None else pd.Series(dtype=float)

def main():
    wl = build(universe.load_us_universe(), universe.load_de_universe(),
               fetch_fn=yahoo.daily_history, index_fetch_fn=_index_close)
    if not wl:                                  # leere Depesche darf Total-Blindheit nicht verdecken
        telegram_bot.send_message(
            "⚠️ Scanner fährt blind — Nacht-Scan lieferte keine Kandidaten (Datenquelle prüfen).")
    state.save_json("state/watchlist.json", wl)
    state.commit_and_push(["state/watchlist.json"], f"state: Watchlist {len(wl)} Titel")

if __name__ == "__main__":
    main()
