import pandas as pd
import trainspotter.config as cfg

def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()

def volume_buildup_ratio(volumes: pd.Series, recent_days: int = cfg.RECENT_VOL_DAYS,
                         baseline_days: int = cfg.BASELINE_VOL_DAYS) -> float:
    if len(volumes) < recent_days + baseline_days:
        return 0.0
    recent = volumes.iloc[-recent_days:].mean()
    baseline = volumes.iloc[-(recent_days + baseline_days):-recent_days].mean()
    return float(recent / baseline) if baseline > 0 else 0.0

def adr_pct(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20) -> float:
    rng = (high - low) / close * 100.0
    return float(rng.iloc[-window:].mean())

def relative_strength(stock_close: pd.Series, index_close: pd.Series, days: int) -> float:
    if len(stock_close) < days + 1 or len(index_close) < days + 1:
        return 0.0
    s = (stock_close.iloc[-1] / stock_close.iloc[-days - 1] - 1) * 100
    i = (index_close.iloc[-1] / index_close.iloc[-days - 1] - 1) * 100
    return float(s - i)

def breakout_level(high: pd.Series, window: int = cfg.BREAKOUT_WINDOW) -> float:
    """Hoechstes Hoch der letzten `window` Tage OHNE den letzten (= heutigen) Tag."""
    return float(high.iloc[-(window + 1):-1].max())

def expected_volume_fraction(elapsed_frac: float) -> float:
    """Erwarteter kumulierter Volumenanteil zum Sitzungsanteil `elapsed_frac`, linear
    interpoliert entlang des U-Kurven-Profils (Eroeffnung/Schluss volumenstark)."""
    x = min(max(elapsed_frac, 0.0), 1.0)
    prof = cfg.VOLUME_PROFILE
    for (x0, y0), (x1, y1) in zip(prof, prof[1:]):
        if x <= x1:
            frac = y0 if x1 == x0 else y0 + (x - x0) / (x1 - x0) * (y1 - y0)
            return min(max(frac, 0.0), 1.0)
    return 1.0

def time_prorated_volume_ratio(volume_today: float, avg_daily_volume: float,
                               elapsed_frac: float) -> float:
    expected = avg_daily_volume * max(expected_volume_fraction(elapsed_frac), 0.05)
    return float(volume_today / expected) if expected > 0 else 0.0

def distance_pct(price: float, level: float) -> float:
    return (price / level - 1) * 100.0
