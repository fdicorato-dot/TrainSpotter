import os, time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
import trainspotter.config as cfg
from trainspotter import calendar_utils as cal, paper_trading as pt, reports, state, telegram_bot as tg, triggers
from trainspotter.data import yahoo

@dataclass
class Deps:
    quotes_fn: Callable
    index_fn: Callable
    send_fn: Callable
    review_fn: Callable
    now_fn: Callable

STATE = {"watchlist": "state/watchlist.json", "alerts": "state/alerts_sent.json",
         "offset": "state/telegram_offset.json"}

def load_context(market: str) -> dict:
    today = datetime.now(timezone.utc).astimezone(cal.TZ[market]).date().isoformat()
    wl = [e for e in state.load_json(STATE["watchlist"], []) if e["market"] == market]
    alerts = state.load_json(STATE["alerts"], {})
    alerts = dict(sorted(alerts.items())[-2:])            # nur gestern+heute behalten
    alerts.setdefault(today, [])
    return {"market": market, "watchlist": wl, "today": today, "alerts_sent": alerts,
            "positions": state.load_json(f"state/positions_{market}.json", [])}

def movers_entries(tickers: list[str], fetch_fn, market: str, known: set[str]) -> list[dict]:
    """Tages-Topmover, die nicht auf der Watchlist stehen: Ad-hoc-Bahnsteig-Eintrag
    mit Ausbruchsniveau aus der Tageshistorie (Spec 6.2, zweite Quelle)."""
    from trainspotter import indicators as ind
    fresh = [t for t in tickers if t not in known]
    if not fresh:
        return []
    out = []
    for t, df in fetch_fn(fresh).items():
        try:
            if len(df) < 60:
                continue
            adr = ind.adr_pct(df["High"], df["Low"], df["Close"])
            if adr < cfg.ADR_MIN_KONS:
                continue
            out.append({"ticker": t, "market": market,
                        "liste": "spekulativ" if adr >= cfg.ADR_MIN_SPEC else "konservativ",
                        "score": cfg.SCORE_MIN, "breakout_level": ind.breakout_level(df["High"]),
                        "adr_pct": round(adr, 2),
                        "avg_volume": float(df["Volume"].iloc[-20:].mean()),
                        "criteria": ["tages_topmover"]})
        except Exception:
            continue
    return out

def persist(ctx: dict):
    state.save_json(f"state/positions_{ctx['market']}.json", ctx["positions"])
    state.save_json(STATE["alerts"], ctx["alerts_sent"])

def run_cycle(ctx: dict, deps: Deps, session_close: bool = False) -> list[str]:
    now = deps.now_fn()
    tickers = [e["ticker"] for e in ctx["watchlist"]] + [p["ticker"] for p in ctx["positions"]]
    quotes = deps.quotes_fn(sorted(set(tickers)))
    index_chg = deps.index_fn()
    elapsed = cal.elapsed_fraction(now, ctx["market"])
    events: list[str] = []
    sent_today = set(ctx["alerts_sent"][ctx["today"]])
    open_ids = {p["id"] for p in ctx["positions"]}
    cands = []
    for e in ctx["watchlist"]:
        q = quotes.get(e["ticker"])
        if not q:
            continue
        try:
            r = triggers.check_trigger(e, q["price"], q["day_volume"], index_chg, elapsed, ctx["today"])
            if r and r["id"] not in open_ids:
                cands.append(r)
        except Exception:
            continue                                     # kranker Ticker stoppt nie den Scan
    for alert in triggers.apply_alert_discipline(cands, sent_today, _sent_counts(ctx)):
        ki = deps.review_fn(alert)
        deps.send_fn(tg.format_alert(alert, ki))
        ctx["alerts_sent"][ctx["today"]].append(alert["id"])
        if alert["status"] == "alert":
            ctx["positions"].append(pt.open_position(alert, now.isoformat()))
            events.append(f"alert:{alert['id']}")
        else:
            events.append(f"missed:{alert['id']}")
    still_open = []
    trades_path = ctx.get("trades_path") or f"state/history/trades_{ctx['market']}.csv"
    for pos in ctx["positions"]:
        q = quotes.get(pos["ticker"])
        if not q:
            still_open.append(pos)
            continue
        evs, trade = pt.update_position(pos, q["price"], now.isoformat(), session_close)
        for ev in evs:
            if ev in ("target1", "trail"):
                deps.send_fn(tg.format_update(ev, pos, q["price"]))
        if trade:
            state.append_trade(trades_path, trade)
            deps.send_fn(tg.format_trade_closed(trade))
            events.append(f"closed:{trade['id']}")
        else:
            still_open.append(pos)
        events += evs
    ctx["positions"] = still_open
    return events

def _sent_counts(ctx: dict) -> dict:
    """Wie viele Alerts je Liste heute schon raus sind (Ticker -> Liste aus der Watchlist)."""
    liste_by_ticker = {e["ticker"]: e["liste"] for e in ctx["watchlist"]}
    counts = {l: 0 for l in cfg.LISTEN}
    for alert_id in ctx["alerts_sent"][ctx["today"]]:
        ticker = alert_id.rsplit("-", 3)[0]               # "NVDA-2026-07-08" -> "NVDA"
        counts[liste_by_ticker.get(ticker, "spekulativ")] += 1
    return counts

def _handle_commands(ctx: dict):
    off = state.load_json(STATE["offset"], {"offset": 0})
    cmds, new_off = tg.poll_commands(off["offset"])
    for c in cmds:
        if c == "/status":
            tg.send_message(reports.format_status_command(ctx["positions"],
                                                          ctx["alerts_sent"][ctx["today"]]))
        elif c == "/stats":
            trades = state.load_trades("state/history/trades_us.csv") + \
                     state.load_trades("state/history/trades_eu.csv")
            tg.send_message(reports.format_stats_command(reports.compute_stats(trades)))
    if new_off != off["offset"]:
        state.save_json(STATE["offset"], {"offset": new_off})

def build_deps(market: str) -> Deps:
    if market == "eu":
        return Deps(quotes_fn=yahoo.intraday_snapshot,
                    index_fn=lambda: yahoo.index_change_pct("eu"),
                    send_fn=tg.send_message, review_fn=_review,
                    now_fn=lambda: datetime.now(timezone.utc))
    from trainspotter.data.finnhub import Finnhub
    fh = Finnhub(os.environ.get("FINNHUB_API_KEY", ""))
    cache: dict = {"cycle": 0, "vol": {}}

    def us_quotes(tickers):
        if cache["cycle"] % cfg.US_VOLUME_REFRESH_CYCLES == 0:
            cache["vol"] = yahoo.intraday_snapshot(tickers)   # Volumen ~15 Min verzoegert
        cache["cycle"] += 1
        out = {}
        for t in tickers:
            q = fh.quote(t)                                   # Preis in Echtzeit
            vol = cache["vol"].get(t, {}).get("day_volume", 0.0)
            if q:
                out[t] = {"price": q["price"], "day_volume": vol}
        return out

    return Deps(quotes_fn=us_quotes, index_fn=lambda: yahoo.index_change_pct("us"),
                send_fn=tg.send_message, review_fn=_review,
                now_fn=lambda: datetime.now(timezone.utc))

def _review(alert):
    from trainspotter import ai_review
    return ai_review.review_trigger(alert, yahoo.headlines(alert["ticker"]))

def run_session(market: str, max_minutes: int):
    now = datetime.now(timezone.utc)
    local_date = now.astimezone(cal.TZ[market]).date()
    if not cal.is_trading_day(local_date, market):
        return
    open_t, close_t = cal.session_bounds(local_date, market)
    hard_end = now + timedelta(minutes=max_minutes)
    ctx, deps = load_context(market), build_deps(market)
    data_fail, cycle_no = 0, 0
    while datetime.now(timezone.utc) < min(close_t, hard_end):
        if datetime.now(timezone.utc) < open_t:
            time.sleep(30)
            continue
        if market == "us" and cycle_no % 10 == 0:         # Spec 6.2: Topmover als 2. Quelle
            known = {e["ticker"] for e in ctx["watchlist"]}
            ctx["watchlist"] += movers_entries(yahoo.top_movers_us(), yahoo.daily_history,
                                               "us", known)
        cycle_no += 1
        try:
            events = run_cycle(ctx, deps)
            data_fail = 0
        except Exception:
            events, data_fail = [], data_fail + 1
            if data_fail == 5:
                tg.send_message("⚠️ Scanner fährt blind — Datenquelle antwortet nicht.")
        if cal.should_poll_commands(datetime.now(timezone.utc), market):
            _handle_commands(ctx)
        if events:
            persist(ctx)
            state.commit_and_push(["state"], f"state: {market} {len(events)} Ereignisse")
        time.sleep(cfg.CYCLE_SECONDS[market])
    if datetime.now(timezone.utc) >= close_t:                 # regulaerer Schluss
        run_cycle(ctx, deps, session_close=True)
    persist(ctx)
    state.commit_and_push(["state"], f"state: {market} Sitzungsende")
