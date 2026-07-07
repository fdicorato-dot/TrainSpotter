import os
import requests

def _api(method: str) -> str | None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    return f"https://api.telegram.org/bot{token}/{method}" if token else None

def send_message(text: str) -> bool:
    url, chat = _api("sendMessage"), os.environ.get("TELEGRAM_CHAT_ID")
    if not url or not chat:
        return False
    for _ in range(3):
        try:
            r = requests.post(url, json={"chat_id": chat, "text": text}, timeout=15)
            if r.ok:
                return True
        except requests.RequestException:
            pass
    return False

def poll_commands(offset: int) -> tuple[list[str], int]:
    url = _api("getUpdates")
    if not url:
        return [], offset
    try:
        r = requests.get(url, params={"offset": offset, "timeout": 0}, timeout=15)
        updates = r.json().get("result", [])
    except (requests.RequestException, ValueError):
        return [], offset
    cmds = []
    for u in updates:
        offset = max(offset, u["update_id"] + 1)
        text = (u.get("message") or {}).get("text", "")
        if text.startswith("/"):
            cmds.append(text.split()[0])
    return cmds, offset

def format_alert(alert: dict, ki: dict | None) -> str:
    warn = f"\n⚠️ {alert['warning']}" if alert.get("warning") else ""
    if alert["status"] == "missed":
        return (f"🚂💨 ZUG VERPASST — {alert['ticker']} [{alert['liste']}]\n"
                f"Schon {alert['dist_pct']:+.1f}% über Ausbruch {alert['breakout_level']:.2f}. "
                f"Nicht hinterherspringen.{warn}")
    lines = [f"🚂 ZUG ERKANNT — {alert['ticker']} [{alert['liste']}]",
             f"Regeln: {', '.join(alert['reasons'])}",
             f"Ausbruch über {alert['breakout_level']:.2f} | Kurs {alert['price']:.2f} ({alert['dist_pct']:+.1f}%)",
             f"Einstieg: {alert['entry']:.2f} | Stop: {alert['stop']:.2f} | Ziel 1: {alert['target1']:.2f}",
             "Danach: Trailing-Stop."]
    if ki and ki.get("einschaetzung"):
        lines.append(f"KI: {ki['einschaetzung']}")
    return "\n".join(lines) + warn

def format_update(event: str, pos: dict, price: float) -> str:
    t = pos["ticker"]
    if event == "target1":
        return f"🔔 {t}: Ziel 1 erreicht ({pos['target1']:.2f}) — halbe Position verbucht, Rest trailt."
    if event == "trail":
        return f"🔔 {t}: Trailing-Stop nachgezogen auf {pos['stop']:.2f} (Kurs {price:.2f})."
    return f"🔔 {t}: {event} (Kurs {price:.2f})."

def format_trade_closed(trade: dict) -> str:
    emo = "✅" if float(trade["pnl_eur"]) >= 0 else "❌"
    return (f"{emo} {trade['ticker']} geschlossen [{trade['reason']}]: "
            f"{float(trade['pnl_eur']):+.2f} € ({float(trade['pnl_pct']):+.1f}%)")
