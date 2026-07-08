from datetime import datetime, timedelta
import trainspotter.config as cfg

def open_position(alert: dict, now_iso: str) -> dict:
    entry = alert["entry"] * (1 + cfg.SLIPPAGE_PCT[alert["liste"]] / 100)
    return {"id": alert["id"], "ticker": alert["ticker"], "market": alert["market"],
            "liste": alert["liste"], "score": alert["score"],
            "criteria": "|".join(alert["reasons"]), "entry": entry,
            "qty": cfg.POSITION_SIZE_EUR / entry, "stop": alert["stop"],
            "target1": alert["target1"], "half_booked": False, "realized": 0.0,
            "trail_prices": [], "opened": now_iso, "open_days": 0}

def _close(pos: dict, price: float, reason: str, now_iso: str) -> dict:
    pnl = pos["realized"] + pos["qty"] * (price - pos["entry"])
    return {"id": pos["id"], "ticker": pos["ticker"], "market": pos["market"],
            "liste": pos["liste"], "score": pos["score"], "criteria": pos["criteria"],
            "opened": pos["opened"], "closed": now_iso,
            "entry": round(pos["entry"], 4), "exit": round(price, 4),
            "qty": round(pos["qty"], 4), "pnl_eur": round(pnl, 2),
            "pnl_pct": round(pnl / cfg.POSITION_SIZE_EUR * 100, 2), "reason": reason}

def _trail_low(pos: dict, now: datetime) -> float:
    cutoff = (now - timedelta(minutes=cfg.TRAIL_WINDOW_MIN)).isoformat()
    pos["trail_prices"] = [(t, p) for t, p in pos["trail_prices"] if t >= cutoff]
    return min(p for _, p in pos["trail_prices"])

def update_position(pos: dict, price: float, now_iso: str,
                    session_close: bool = False) -> tuple[list[str], dict | None]:
    now = datetime.fromisoformat(now_iso)
    pos["trail_prices"].append((now_iso, price))
    events: list[str] = []
    if price <= pos["stop"]:
        reason = "trail_stop" if pos["half_booked"] else "stop"
        return ["stop"], _close(pos, price, reason, now_iso)
    if not pos["half_booked"] and price >= pos["target1"]:
        half = pos["qty"] / 2
        pos["realized"] += half * (pos["target1"] - pos["entry"])
        pos["qty"], pos["half_booked"] = half, True
        events.append("target1")
    if pos["half_booked"]:
        new_stop = _trail_low(pos, now) * (1 - cfg.TRAIL_BUFFER_PCT / 100)
        if new_stop > pos["stop"]:
            pos["stop"] = round(new_stop, 4)
            events.append("trail")
    if session_close:
        if pos["liste"] == "spekulativ":
            return events + ["session_close"], _close(pos, price, "tagesschluss", now_iso)
        pos["open_days"] += 1
        if pos["open_days"] >= cfg.MAX_HOLD_DAYS_KONS:
            return events + ["session_close"], _close(pos, price, "max_haltedauer", now_iso)
    return events, None
