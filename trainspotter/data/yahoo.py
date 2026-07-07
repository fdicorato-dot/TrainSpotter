"""Einzige Stelle im Projekt, die yfinance importiert (austauschbare Quelle)."""
import pandas as pd
import yfinance as yf
import trainspotter.config as cfg

def split_batch(df: pd.DataFrame, tickers: list[str]) -> dict[str, pd.DataFrame]:
    out = {}
    if df is None or df.empty:
        return out
    for t in tickers:
        try:
            sub = df[t].dropna(how="all") if isinstance(df.columns, pd.MultiIndex) else df
            if not sub.empty and "Close" in sub:
                out[t] = sub[["Open", "High", "Low", "Close", "Volume"]]
        except (KeyError, IndexError):
            continue
    return out

def daily_history(tickers: list[str], period: str = "2y") -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), 400):               # Batches gegen Timeouts
        chunk = tickers[i:i + 400]
        try:
            df = yf.download(chunk, period=period, interval="1d", group_by="ticker",
                             auto_adjust=True, progress=False, threads=True)
            out.update(split_batch(df, chunk))
        except Exception:
            continue                                     # Batch darf ausfallen
    return out

def intraday_snapshot(tickers: list[str]) -> dict[str, dict]:
    try:
        df = yf.download(tickers, period="1d", interval="15m", group_by="ticker",
                         auto_adjust=True, progress=False, threads=True)
    except Exception:
        return {}
    out = {}
    for t, sub in split_batch(df, tickers).items():
        out[t] = {"price": float(sub["Close"].iloc[-1]),
                  "day_volume": float(sub["Volume"].sum())}
    return out

def index_change_pct(market: str) -> float:
    try:
        h = yf.Ticker(cfg.INDEX_SYMBOL[market]).history(period="2d", interval="1d")
        prev, last = float(h["Close"].iloc[-2]), float(h["Close"].iloc[-1])
        return (last / prev - 1) * 100.0
    except Exception:
        return 0.0                                       # neutral bei Datenausfall

def top_movers_us(limit: int = 25) -> list[str]:
    try:
        r = yf.screen("day_gainers", count=limit)
        return [q["symbol"] for q in r.get("quotes", [])]
    except Exception:
        return []

def headlines(ticker: str, limit: int = 5) -> list[str]:
    try:
        news = yf.Ticker(ticker).news or []
        return [n.get("content", {}).get("title") or n.get("title", "") for n in news[:limit]]
    except Exception:
        return []
