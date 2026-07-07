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
