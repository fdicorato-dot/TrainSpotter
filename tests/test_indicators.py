import pandas as pd, pytest
from trainspotter import indicators as ind

def test_sma():
    assert ind.sma(pd.Series([1, 2, 3, 4, 5]), 5).iloc[-1] == 3.0

def test_volume_buildup_ratio():
    vols = pd.Series([100.0] * 20 + [200.0] * 5)   # Basis 100, letzte 5 Tage 200
    assert ind.volume_buildup_ratio(vols) == pytest.approx(2.0)

def test_volume_buildup_zu_wenig_daten():
    assert ind.volume_buildup_ratio(pd.Series([100.0] * 10)) == 0.0

def test_adr_pct():
    n = 20
    df = {"h": pd.Series([105.0] * n), "l": pd.Series([95.0] * n), "c": pd.Series([100.0] * n)}
    assert ind.adr_pct(df["h"], df["l"], df["c"]) == pytest.approx(10.0)

def test_relative_strength():
    stock = pd.Series([100, 102, 104, 106, 108, 110.0])   # +10 % ueber 5 Tage
    index = pd.Series([100, 101, 102, 103, 104, 105.0])   # +5 %
    assert ind.relative_strength(stock, index, days=5) == pytest.approx(5.0)

def test_breakout_level_ohne_heute():
    highs = pd.Series([10, 12, 11, 15, 14, 99.0])  # 99 ist "heute" -> zaehlt nicht
    assert ind.breakout_level(highs, window=5) == 15.0

def test_time_prorated_volume_ratio():
    # 600k bei 30 % Sitzung, Schnitt 1M/Tag -> erwartet 300k -> Ratio 2.0
    assert ind.time_prorated_volume_ratio(600_000, 1_000_000, 0.3) == pytest.approx(2.0)

def test_distance_pct():
    assert ind.distance_pct(95.0, 100.0) == pytest.approx(-5.0)
    assert ind.distance_pct(104.0, 100.0) == pytest.approx(4.0)
