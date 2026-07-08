import pandas as pd
import trainspotter.config as cfg
from trainspotter import indicators as ind

def platform_score(ticker: str, df: pd.DataFrame, index_close: pd.Series, market: str) -> dict | None:
    if df is None or len(df) < 60:
        return None
    close = df["Close"]
    price = float(close.iloc[-1])
    dollar_vol = float((close * df["Volume"]).iloc[-20:].mean())
    if price < cfg.MIN_PRICE or dollar_vol < cfg.MIN_DOLLAR_VOLUME:
        return None
    adr = ind.adr_pct(df["High"], df["Low"], close)
    if adr >= cfg.ADR_MIN_SPEC:
        liste = "spekulativ"
    elif adr >= cfg.ADR_MIN_KONS:
        liste = "konservativ"
    else:
        return None                                      # bewegt sich historisch nicht
    level = ind.breakout_level(df["High"])
    dist = ind.distance_pct(price, level)
    if dist > cfg.MAX_ABOVE_BREAKOUT_PCT:
        return None                                      # Zug gestern schon abgefahren
    score, criteria = 0, []
    vb = ind.volume_buildup_ratio(df["Volume"])
    if vb >= cfg.VOL_BUILDUP_RATIO:
        score += 25; criteria.append(f"volumen_aufbau:{vb:.1f}x")
    if dist >= -cfg.NEAR_BREAKOUT_PCT:
        score += 25; criteria.append(f"nahe_ausbruch:{dist:.1f}%")
    sma20, sma50 = ind.sma(close, 20), ind.sma(close, 50)
    if price > sma20.iloc[-1] > sma50.iloc[-1] and sma20.iloc[-1] > sma20.iloc[-6]:
        score += 20; criteria.append("trend_intakt")
    rs = ind.relative_strength(close, index_close, cfg.RS_DAYS)
    if rs > 5:
        score += 20; criteria.append(f"rel_staerke:+{rs:.0f}pp")
    elif rs > 0:
        score += 10; criteria.append(f"rel_staerke:+{rs:.0f}pp")
    if score < cfg.SCORE_MIN:
        return None
    return {"ticker": ticker, "market": market, "liste": liste, "score": score,
            "breakout_level": round(level, 4), "adr_pct": round(adr, 2),
            "avg_volume": float(df["Volume"].iloc[-20:].mean()), "criteria": criteria}

def build_watchlist(entries: list[dict]) -> list[dict]:
    """Quotierte Auswahl je (Markt, Liste): jeder Eimer bekommt hoechstens seine Quote,
    freie Restplaetze werden marktuebergreifend nachbesetzt. Sortierschluessel ueberall
    (Score absteigend, Ø-Volumen absteigend) — das Volumen als stetiger Tiebreaker
    ersetzt die fruehere alphabetische Zufallsreihenfolge."""
    def key(e):
        return (e["score"], e.get("avg_volume", 0.0))
    ranked = sorted(entries, key=key, reverse=True)
    selected, leftover = [], []
    remaining = dict(cfg.WATCHLIST_QUOTA)
    for e in ranked:
        bucket = (e.get("market"), e.get("liste"))
        if remaining.get(bucket, 0) > 0:
            remaining[bucket] -= 1
            selected.append(e)
        else:
            leftover.append(e)
    free = cfg.WATCHLIST_SIZE - len(selected)
    if free > 0:
        selected += leftover[:free]                       # Restplaetze nachbesetzen
    return selected
