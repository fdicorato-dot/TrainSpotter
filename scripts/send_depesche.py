import sys
from datetime import date

import trainspotter.config as cfg
from trainspotter import reports, state, telegram_bot as tg

if __name__ == "__main__":
    wl = state.load_json("state/watchlist.json", [])
    report_url = f"{cfg.REPORT_URL_BASE}/{date.today().isoformat()}.html"
    ok = tg.send_message(reports.format_depesche(wl, report_url=report_url))
    sys.exit(0 if ok else 1)                            # fehlgeschlagener Versand = roter Lauf
