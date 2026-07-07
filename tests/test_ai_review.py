import subprocess
from trainspotter import ai_review

ALERT = {"ticker": "NVDA", "liste": "spekulativ", "price": 101.5, "breakout_level": 100.0,
         "vol_ratio": 2.5, "reasons": ["r1"], "score": 90}

class FakeProc:
    def __init__(self, out):
        self.stdout, self.returncode = out, 0

def test_parst_json_aus_antwort(monkeypatch):
    out = 'Hier: {"einschaetzung": "Zug faehrt.", "katalysator": "Earnings", "risiko": "Markt", "liste_ok": true}'
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc(out))
    r = ai_review.review_trigger(ALERT, ["News 1"])
    assert r["einschaetzung"] == "Zug faehrt." and r["liste_ok"] is True

def test_none_bei_muell(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc("kein json"))
    assert ai_review.review_trigger(ALERT, []) is None

def test_none_bei_timeout(monkeypatch):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired("claude", 180)
    monkeypatch.setattr(subprocess, "run", boom)
    assert ai_review.review_trigger(ALERT, []) is None
