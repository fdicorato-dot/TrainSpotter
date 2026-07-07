import json, re, subprocess

PROMPT = """Du bist nüchterner Trading-Analyst. Ein regelbasierter Momentum-Scanner hat einen Ausbruch erkannt:
Ticker: {ticker} | Liste: {liste} | Kurs: {price} | Ausbruchsniveau: {level}
Volumen: {vol}x zeitanteiliger Schnitt | Regel-Score: {score} | Regeln: {reasons}
Aktuelle Schlagzeilen: {headlines}

Bewerte NUR auf Basis dieser Daten. Antworte AUSSCHLIESSLICH mit einem JSON-Objekt:
{{"einschaetzung": "<max 2 Saetze deutsch>", "katalysator": "<string oder null>",
"risiko": "<1 Satz>", "liste_ok": <true/false>}}"""

def review_trigger(alert: dict, headlines: list[str]) -> dict | None:
    prompt = PROMPT.format(ticker=alert["ticker"], liste=alert["liste"], price=alert["price"],
                           level=alert["breakout_level"], vol=alert["vol_ratio"],
                           score=alert["score"], reasons=", ".join(alert["reasons"]),
                           headlines="; ".join(headlines) or "keine")
    try:
        r = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=180)
        m = re.search(r"\{.*\}", r.stdout, re.S)
        d = json.loads(m.group(0))
        return d if "einschaetzung" in d else None
    except Exception:
        return None    # KI-Ausfall darf nie einen Alert verhindern
