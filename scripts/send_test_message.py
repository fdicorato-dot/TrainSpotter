from trainspotter import telegram_bot as tg

if __name__ == "__main__":
    ok = tg.send_message("🚂 TrainSpotter Testnachricht — Verbindung steht.")
    print("OK" if ok else "FEHLER: Token/Chat-ID pruefen")
