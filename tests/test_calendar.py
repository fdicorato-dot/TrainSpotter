from datetime import date, datetime, timezone
from trainspotter import calendar_utils as cal

def test_wochenende_und_feiertage():
    assert not cal.is_trading_day(date(2026, 7, 11), "us")      # Samstag
    assert not cal.is_trading_day(date(2026, 7, 3), "us")       # 4.Juli beobachtet
    assert cal.is_trading_day(date(2026, 7, 3), "eu")           # DE offen
    assert not cal.is_trading_day(date(2026, 4, 6), "eu")       # Ostermontag
    assert cal.is_trading_day(date(2026, 7, 8), "us")

def test_session_bounds_eu():
    o, c = cal.session_bounds(date(2026, 7, 8), "eu")
    assert (o.hour, o.minute) == (9, 0) and (c.hour, c.minute) == (17, 30)

def test_elapsed_fraction_mitte():
    # 12:00 UTC = 14:00 Berlin -> 5h von 8.5h EU-Sitzung
    now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
    assert abs(cal.elapsed_fraction(now, "eu") - 5 / 8.5) < 0.01

def test_should_poll_commands():
    vor = datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc)    # 12:00 Berlin
    nach = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)   # 16:00 Berlin
    assert cal.should_poll_commands(vor, "eu")
    assert not cal.should_poll_commands(nach, "eu")
    assert cal.should_poll_commands(nach, "us")
