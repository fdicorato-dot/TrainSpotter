import pandas as pd
import trainspotter.config as cfg
from trainspotter import night_scan

def simulate_trade(entry: dict, df: pd.DataFrame, day_idx: int) -> dict | None:
    level, liste = entry["breakout_level"], entry["liste"]
    d0 = df.iloc[day_idx]
    if d0["High"] <= level or d0["Open"] >= level * 1.04:
        return None
    buy = max(level, float(d0["Open"])) * (1 + cfg.SLIPPAGE_PCT / 100)
    stop = level * (1 - cfg.STOP_PCT[liste] / 100)
    target1 = buy * (1 + cfg.TARGET1_PCT[liste] / 100)
    horizon = 1 if liste == "spekulativ" else cfg.MAX_HOLD_DAYS_KONS
    half_done, pnl_pct = False, 0.0
    last = min(day_idx + horizon, len(df)) - 1
    for i in range(day_idx, last + 1):
        d = df.iloc[i]
        if d["Low"] <= stop:                              # pessimistisch: Stop vor Ziel
            frac = 0.5 if half_done else 1.0
            return _result(entry, i, buy, stop, pnl_pct + frac * (stop / buy - 1) * 100,
                           "trail_stop" if half_done else "stop")
        if not half_done and d["High"] >= target1:
            pnl_pct += 0.5 * (target1 / buy - 1) * 100
            half_done, stop = True, buy                   # Rest: Breakeven-Stop (Tagesbasis)
    exit_price = float(df.iloc[last]["Close"])
    frac = 0.5 if half_done else 1.0
    reason = "tagesschluss" if liste == "spekulativ" else "zeitausstieg"
    return _result(entry, last, buy, exit_price, pnl_pct + frac * (exit_price / buy - 1) * 100, reason)

def _result(entry, day, buy, exit_price, pnl_pct, reason):
    return {"ticker": entry["ticker"], "day": int(day), "liste": entry["liste"],
            "entry": round(buy, 4), "exit": round(float(exit_price), 4),
            "pnl_pct": round(pnl_pct, 3), "reason": reason}

def simulate(daily: dict[str, pd.DataFrame], index_close: pd.Series,
             market: str, start_idx: int = 60) -> pd.DataFrame:
    trades = []
    aligned, skipped = {}, 0
    for ticker, df in daily.items():                      # positionelles Slicing braucht
        if len(df) == len(index_close) and df.index.equals(index_close.index):
            aligned[ticker] = df                          # deckungsgleiche Indizes, sonst
        else:                                             # falsche RS-/Folgetag-Mathematik
            skipped += 1
    n = len(index_close)
    for t in range(start_idx, n - 1):
        for ticker, df in aligned.items():
            if len(df) <= t + 1:
                continue
            try:
                e = night_scan.platform_score(ticker, df.iloc[:t + 1], index_close.iloc[:t + 1], market)
                if e:
                    tr = simulate_trade(e, df, t + 1)
                    if tr:
                        trades.append(tr)
            except Exception:
                continue
    result = pd.DataFrame(trades)
    result.attrs["skipped"] = skipped
    return result
