"""Simulierter Handelstag aus aufgezeichneten Daten. Kein Netz, kein Git, kein Telegram."""
import json, os, sys, tempfile
from datetime import datetime
from trainspotter.live_observer import Deps, run_cycle

def run(fixture_path: str) -> dict:
    os.environ["TRAINSPOTTER_NO_GIT"] = "1"
    fx = json.load(open(fixture_path))
    ctx = {"market": "us", "watchlist": fx["watchlist"], "positions": [],
           "alerts_sent": {fx["today"]: []}, "today": fx["today"],
           "trades_path": os.path.join(tempfile.mkdtemp(), "trades.csv")}
    sent, alerts, closed = [], 0, 0
    for i, cyc in enumerate(fx["cycles"]):
        deps = Deps(quotes_fn=lambda ts, c=cyc: c["quotes"], index_fn=lambda c=cyc: c["index"],
                    send_fn=lambda t: sent.append(t) or True, review_fn=lambda a: None,
                    now_fn=lambda c=cyc: datetime.fromisoformat(c["time"]))
        events = run_cycle(ctx, deps, session_close=(i == len(fx["cycles"]) - 1))
        alerts += sum(1 for e in events if e.startswith("alert:"))
        closed += sum(1 for e in events if e.startswith("closed:"))
    for m in sent:
        print(m, "\n---")
    return {"alerts": alerts, "closed": closed, "open_end": len(ctx["positions"])}

if __name__ == "__main__":
    print(run(sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/recorded_day.json"))
