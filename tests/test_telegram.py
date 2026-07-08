from trainspotter import telegram_bot as tg

ALERT = {"id": "NVDA-2026-07-08", "ticker": "NVDA", "name": "NVIDIA Corporation",
         "liste": "spekulativ", "status": "alert",
         "price": 101.5, "entry": 101.5, "stop": 94.0, "target1": 111.65,
         "breakout_level": 100.0, "vol_ratio": 2.5, "dist_pct": 1.5,
         "reasons": ["volumen_aufbau:2.0x", "ausbruch_ueber:100.00", "volumen:2.5x_zeitanteilig"],
         "warning": None, "market": "us", "score": 90}

def test_format_alert_golden():
    text = tg.format_alert(ALERT, {"einschaetzung": "Ausbruch wird von News getragen."})
    assert text == ("🚂 ZUG ERKANNT — NVDA (NVIDIA Corporation) [spekulativ]\n"
                    "Regeln: volumen_aufbau:2.0x, ausbruch_ueber:100.00, volumen:2.5x_zeitanteilig\n"
                    "Ausbruch über 100.00 | Kurs 101.50 (+1.5%)\n"
                    "Einstieg: 101.50 | Stop: 94.00 | Ziel 1: 111.65\n"
                    "Danach: Trailing-Stop.\n"
                    "KI: Ausbruch wird von News getragen.")

def test_format_alert_ohne_namen_keine_klammer():
    ohne = {k: v for k, v in ALERT.items() if k != "name"}
    assert tg.format_alert(ohne, None).startswith("🚂 ZUG ERKANNT — NVDA [spekulativ]")
    gleich = ALERT | {"name": "NVDA"}                     # Name == Ticker -> kein "NVDA (NVDA)"
    assert tg.format_alert(gleich, None).startswith("🚂 ZUG ERKANNT — NVDA [spekulativ]")

def test_format_alert_verpasst_und_warnung():
    a = ALERT | {"status": "missed", "dist_pct": 7.0, "warning": "Markt-Gegenwind: Index -2.0% heute"}
    text = tg.format_alert(a, None)
    assert text.startswith("🚂💨 ZUG VERPASST — NVDA (NVIDIA Corporation) [spekulativ]")
    assert "Nicht hinterherspringen" in text and "⚠️ Markt-Gegenwind" in text

def test_format_update():
    pos = {"ticker": "NVDA", "stop": 109.95, "target1": 111.65, "liste": "spekulativ"}
    assert "Ziel 1 erreicht" in tg.format_update("target1", pos, 111.7)
    assert "nachgezogen" in tg.format_update("trail", pos, 111.7)

def test_send_message_ohne_token_false(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert tg.send_message("hi") is False


def test_lange_nachricht_wird_an_zeilengrenzen_gesplittet(monkeypatch):
    import requests as rq
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    calls = []

    class OK:
        ok = True

    monkeypatch.setattr(rq, "post", lambda url, json, timeout: calls.append(json["text"]) or OK())
    text = "\n".join(f"Zeile {i} " + "x" * 60 for i in range(100))   # ~6800 Zeichen
    assert tg.send_message(text) is True
    assert len(calls) >= 2                                # gesplittet
    assert all(len(c) <= tg.MAX_MESSAGE_LEN for c in calls)
    assert "\n".join(calls) == text                       # nichts verloren

def test_kurze_nachricht_bleibt_ein_stueck():
    assert tg._split_message("hallo") == ["hallo"]
