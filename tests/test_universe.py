from pathlib import Path
from trainspotter import universe


def test_parse_nasdaq_ohne_testissues_und_etfs():
    text = Path("tests/fixtures/nasdaqlisted_sample.txt").read_text()
    syms = universe.parse_nasdaq_file(text)
    assert syms == ["AAPL", "NVDA"]          # kein Test-Issue, kein ETF, keine Fusszeile


def test_de_universe_laedt_und_hat_de_suffix():
    syms = universe.load_de_universe()
    assert len(syms) >= 40 and all(s.endswith(".DE") for s in syms)
    assert "SAP.DE" in syms


def test_parse_nasdaq_names_klarnamen_ohne_suffix():
    text = Path("tests/fixtures/nasdaqlisted_sample.txt").read_text()
    names = universe.parse_nasdaq_names(text)
    assert names == {"AAPL": "Apple Inc.", "NVDA": "NVIDIA Corporation"}


def test_load_de_names_liefert_klarnamen():
    names = universe.load_de_names()
    assert names["SAP.DE"] == "SAP"
    assert names["RHM.DE"] == "Rheinmetall"
    assert len(names) >= 40
