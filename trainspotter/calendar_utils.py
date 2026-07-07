from datetime import date, datetime, time
from zoneinfo import ZoneInfo

TZ = {"us": ZoneInfo("America/New_York"), "eu": ZoneInfo("Europe/Berlin")}
OPEN_CLOSE = {"us": (time(9, 30), time(16, 0)), "eu": (time(9, 0), time(17, 30))}

US_HOLIDAYS_2026 = {"2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
                    "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25"}
DE_HOLIDAYS_2026 = {"2026-01-01", "2026-04-03", "2026-04-06", "2026-05-01", "2026-05-25",
                    "2026-12-24", "2026-12-25", "2026-12-31"}
HOLIDAYS = {"us": US_HOLIDAYS_2026, "eu": DE_HOLIDAYS_2026}

def is_trading_day(d: date, market: str) -> bool:
    return d.weekday() < 5 and d.isoformat() not in HOLIDAYS[market]

def session_bounds(d: date, market: str):
    tz = TZ[market]
    o, c = OPEN_CLOSE[market]
    return datetime.combine(d, o, tz), datetime.combine(d, c, tz)

def elapsed_fraction(now_utc: datetime, market: str) -> float:
    local = now_utc.astimezone(TZ[market])
    o, c = session_bounds(local.date(), market)
    total = (c - o).total_seconds()
    return min(max((local - o).total_seconds() / total, 0.0), 1.0)

def should_poll_commands(now_utc: datetime, market: str) -> bool:
    if market == "us":
        return True
    return now_utc.astimezone(TZ["eu"]).time() < time(15, 15)
