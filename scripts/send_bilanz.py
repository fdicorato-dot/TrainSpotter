from datetime import date
from trainspotter import reports, state, telegram_bot as tg

if __name__ == "__main__":
    trades = state.load_trades("state/history/trades_us.csv") + \
             state.load_trades("state/history/trades_eu.csv")
    today = date.today().isoformat()
    today_trades = [t for t in trades if t["closed"].startswith(today)]
    open_pos = state.load_json("state/positions_us.json", []) + \
               state.load_json("state/positions_eu.json", [])
    ok = tg.send_message(reports.format_bilanz(reports.compute_stats(trades), open_pos, today_trades))
    import sys
    sys.exit(0 if ok else 1)                            # fehlgeschlagener Versand = roter Lauf
