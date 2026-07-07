from trainspotter import reports, state, telegram_bot as tg

if __name__ == "__main__":
    wl = state.load_json("state/watchlist.json", [])
    tg.send_message(reports.format_depesche(wl))     # Heartbeat: sendet auch bei leer
