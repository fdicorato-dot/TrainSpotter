import json, os, subprocess
from trainspotter import state

def test_save_load_roundtrip(tmp_path):
    p = str(tmp_path / "x.json")
    state.save_json(p, {"a": 1})
    assert state.load_json(p, {}) == {"a": 1}

def test_load_defekte_datei_gibt_default(tmp_path):
    p = tmp_path / "kaputt.json"
    p.write_text("{nicht json")
    assert state.load_json(str(p), {"ok": True}) == {"ok": True}

def test_load_fehlende_datei_gibt_default(tmp_path):
    assert state.load_json(str(tmp_path / "fehlt.json"), []) == []

def test_append_und_load_trades(tmp_path):
    p = str(tmp_path / "trades.csv")
    t = {f: "" for f in state.TRADE_FIELDS} | {"id": "NVDA-2026-07-08", "pnl_eur": "12.5"}
    state.append_trade(p, t)
    state.append_trade(p, t | {"id": "SAP-2026-07-08"})
    rows = state.load_trades(p)
    assert len(rows) == 2 and rows[0]["id"] == "NVDA-2026-07-08"

def test_commit_noop_ohne_git(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAINSPOTTER_NO_GIT", "1")
    assert state.commit_and_push(["egal.json"], "msg") is True

class _FakeResult:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode

def test_commit_nichts_zu_tun_ist_erfolg(monkeypatch):
    monkeypatch.delenv("TRAINSPOTTER_NO_GIT", raising=False)
    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        if cmd[:3] == ["git", "status", "--porcelain"]:
            return _FakeResult(stdout="", returncode=0)
        raise AssertionError(f"unerwarteter Aufruf: {cmd}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert state.commit_and_push(["state/x.json"], "msg") is True
    assert not any("commit" in c for c in calls)

def test_commit_fehler_ist_misserfolg(monkeypatch):
    monkeypatch.delenv("TRAINSPOTTER_NO_GIT", raising=False)

    def fake_run(cmd, *args, **kwargs):
        if cmd[:3] == ["git", "status", "--porcelain"]:
            return _FakeResult(stdout="M state/x.json\n", returncode=0)
        if cmd[:2] == ["git", "add"]:
            return _FakeResult(stdout="", returncode=0)
        if cmd[:2] == ["git", "commit"]:
            return _FakeResult(stdout="", returncode=1)
        raise AssertionError(f"unerwarteter Aufruf: {cmd}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert state.commit_and_push(["state/x.json"], "msg") is False
