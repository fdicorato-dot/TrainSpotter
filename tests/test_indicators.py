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

def test_expected_volume_fraction_u_kurve():
    # Stuetzpunkte exakt treffen
    assert ind.expected_volume_fraction(0.08) == pytest.approx(0.12)
    assert ind.expected_volume_fraction(0.5) == pytest.approx(0.52)
    # linear zwischen (0.15,0.20) und (0.5,0.52): 0.20 + (0.3-0.15)/0.35*0.32
    assert ind.expected_volume_fraction(0.3) == pytest.approx(0.337142857, abs=1e-6)
    # Clipping ausserhalb [0,1]
    assert ind.expected_volume_fraction(-1.0) == 0.0
    assert ind.expected_volume_fraction(2.0) == 1.0

def test_time_prorated_volume_ratio():
    # elapsed 0.3 -> Anteil 0.337142857 -> 600000/(1e6*0.337142857) = 1.7797
    assert ind.time_prorated_volume_ratio(600_000, 1_000_000, 0.3) == pytest.approx(1.7797, abs=0.001)
    # elapsed 0.08 (Morgen) -> Anteil 0.12 -> 600000/120000 = 5.0 (kein Ueberschaetzen mehr)
    assert ind.time_prorated_volume_ratio(600_000, 1_000_000, 0.08) == pytest.approx(5.0, abs=0.001)
    # elapsed 0.0 -> Floor 0.05 greift -> 600000/50000 = 12.0
    assert ind.time_prorated_volume_ratio(600_000, 1_000_000, 0.0) == pytest.approx(12.0, abs=0.001)

def test_distance_pct():
    assert ind.distance_pct(95.0, 100.0) == pytest.approx(-5.0)
    assert ind.distance_pct(104.0, 100.0) == pytest.approx(4.0)
