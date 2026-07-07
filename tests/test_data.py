import pandas as pd
from trainspotter.data import yahoo, finnhub

def _batch_df():
    cols = pd.MultiIndex.from_product([["AAA", "BBB"], ["Open", "High", "Low", "Close", "Volume"]])
    data = [[1, 2, 0.5, 1.5, 100, 10, 20, 5, 15, 1000]] * 3
    return pd.DataFrame(data, columns=cols)

def test_split_batch():
    out = yahoo.split_batch(_batch_df(), ["AAA", "BBB", "CCC"])
    assert set(out) == {"AAA", "BBB"}                    # CCC fehlt -> weggelassen
    assert list(out["AAA"].columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert out["BBB"]["Close"].iloc[-1] == 15

def test_finnhub_quote_parst_antwort(monkeypatch):
    fh = finnhub.Finnhub("key", min_interval=0)
    monkeypatch.setattr(fh, "_get", lambda path, params: {"c": 101.5, "pc": 100.0})
    assert fh.quote("NVDA") == {"price": 101.5}

def test_finnhub_quote_none_bei_fehler(monkeypatch):
    fh = finnhub.Finnhub("key", min_interval=0)
    monkeypatch.setattr(fh, "_get", lambda path, params: None)
    assert fh.quote("NVDA") is None
