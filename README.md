# TrainSpotter

## 1. Was ist TrainSpotter

TrainSpotter ist ein Momentum-Scanner, der die Aktienuniversen Europa (DAX/Xetra) und USA täglich nach anziehenden Kursbewegungen durchsucht und die Treffer über Telegram meldet. Er führt zwei Listen — eine **Watchlist** beobachteter Kandidaten und ein **Paper-Trading-Depot** simulierter Positionen — und protokolliert jeden simulierten Ein- und Ausstieg, sodass sich die Trefferqualität über die Zeit auswerten lässt. Der vollständige fachliche Entwurf steht in der Spec unter [`docs/superpowers/specs/2026-07-07-trainspotter-design.md`](docs/superpowers/specs/2026-07-07-trainspotter-design.md).

> **Disclaimer:** TrainSpotter liefert **Analyse, keine Anlageberatung**. Alle Signale, Depots und Kennzahlen sind Simulationen zu Informationszwecken. Anlageentscheidungen triffst du eigenverantwortlich.

## 2. Einmalige Einrichtung

Der Betrieb läuft vollständig über GitHub Actions — kein eigener Server nötig. Arbeite diese Checkliste einmal von oben nach unten ab:

- [ ] **GitHub-Repo öffentlich anlegen** und den Code pushen. (Öffentlich ist wichtig: private Repos haben nur begrenzte kostenlose Actions-Minuten, die für den Tagesbetrieb nicht reichen.)
- [ ] **Telegram-Bot erstellen:** In Telegram [@BotFather](https://t.me/BotFather) anschreiben → `/newbot` → Namen vergeben. BotFather liefert den Token → das ist `TELEGRAM_BOT_TOKEN`.
- [ ] **Chat-ID ermitteln:** Den eigenen neuen Bot **einmal anschreiben** (irgendeine Nachricht). Dann im Browser `https://api.telegram.org/bot<TOKEN>/getUpdates` aufrufen (`<TOKEN>` einsetzen). Im JSON steht `"chat":{"id":...}` → dieser Wert ist `TELEGRAM_CHAT_ID`.
- [ ] **Finnhub-Account anlegen:** Kostenlosen Account auf [finnhub.io](https://finnhub.io) erstellen → API-Key aus dem Dashboard kopieren → `FINNHUB_API_KEY`.
- [ ] **Claude-Token erzeugen:** Lokal (mit installiertem Claude Code) `claude setup-token` ausführen → der ausgegebene Wert ist `CLAUDE_CODE_OAUTH_TOKEN`.
- [ ] **Alle 4 Werte als Repo-Secrets hinterlegen:** `Settings → Secrets and variables → Actions → New repository secret`. Anzulegen sind exakt:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
  - `FINNHUB_API_KEY`
  - `CLAUDE_CODE_OAUTH_TOKEN`
- [ ] **Actions aktivieren:** Im Reiter `Actions` die Workflows für dieses Repo freischalten (bei geforktem/neuem Repo einmalig bestätigen).
- [ ] **Testlauf:** Workflow **`depesche`** manuell starten (`Actions → depesche → Run workflow`, das ist der `workflow_dispatch`-Trigger). Es muss eine Telegram-Nachricht ankommen. Alternativ lokal testen (mit gesetzten Umgebungsvariablen `TELEGRAM_BOT_TOKEN` und `TELEGRAM_CHAT_ID`):
  ```bash
  python -m scripts.send_test_message
  ```

> **Hinweis zum Aufruf:** Alle Skripte werden als Modul gestartet — `python -m scripts.<name>`. Der direkte Aufruf `python scripts/<name>.py` schlägt fehl (die Bibliothek `trainspotter` liegt dann nicht im `sys.path`).

## 3. Betrieb

Alle Workflows laufen automatisch von Montag bis Freitag. Die Cron-Zeiten in den Workflow-Dateien sind in **UTC** angegeben; die folgende Tabelle rechnet auf **MESZ (Sommerzeit, UTC+2)** um. Jeder Workflow lässt sich zusätzlich jederzeit per `workflow_dispatch` von Hand starten.

| Uhrzeit (MESZ) | Workflow | Aufgabe |
|---|---|---|
| 07:00 | `night-scan` | Nacht-Scan: Universum durchsuchen, Kandidaten für den Tag vorbereiten |
| 08:45 | `depesche` | Morgen-Depesche mit Watchlist/Depot-Stand — **Heartbeat** |
| 08:55 → 14:30 | `observer-eu` (Teil 1) | EU-Beobachter, laufende Kursüberwachung während der Xetra-Handelszeit |
| 14:25 → 17:30 | `observer-eu` (Teil 2) | EU-Beobachter, zweite Schicht bis Handelsschluss |
| 15:20 → 20:50 | `observer-us` (Teil 1) | US-Beobachter, laufende Überwachung ab US-Handelsstart |
| 20:50 → 22:00 | `observer-us` (Teil 2) | US-Beobachter, zweite Schicht bis US-Schluss |
| 22:15 | `bilanz` | Tagesbilanz: Abschlüsse, Depot-Stand, Kennzahlen — **Heartbeat** |

Die Beobachter-Workflows laufen jeweils in zwei Schichten (GitHub-Läufe sind zeitlich begrenzt); die zweite Schicht klinkt sich per `concurrency` an die erste an und deckt so den ganzen Handelstag ab.

> **Heartbeat-Regel:** `depesche` (morgens) und `bilanz` (abends) sind die Lebenszeichen des Systems. **Bleibt eine der beiden Nachrichten aus, steht das System** — dann im Reiter `Actions` das Log des betroffenen Workflows ansehen (häufigste Ursachen: abgelaufener Secret/Token, API-Limit, GitHub-Ausfall).

## 4. Backtest

Bevor du den Live-Signalen vertraust, validiere die Regeln historisch. Der Backtest spielt die Momentum-Logik über vergangene Jahre durch:

```bash
python -m scripts.run_backtest --market eu --years 3
```

Für den US-Markt `--market us` setzen. Prüfe erst, ob die Regeln im Backtest plausible Ergebnisse liefern, und vertraue erst dann dem Live-Betrieb.

## 5. Wartung / Backlog

- **Feiertagslisten jährlich pflegen:** Die Börsen-Feiertage stehen in [`trainspotter/calendar_utils.py`](trainspotter/calendar_utils.py). Einmal pro Jahr das kommende Jahr ergänzen, sonst laufen Scans an Feiertagen ins Leere.
- **Winterzeit (MEZ, UTC+1):** Die Cron-Zeiten stehen fest in UTC. In der Winterzeit verschieben sich alle Läufe um eine Stunde nach hinten (z. B. Depesche dann 07:45 statt 08:45). Wer die lokalen Zeiten konstant halten will, verschiebt die Crons in den Workflow-Dateien beim Zeitumstieg um **1 Stunde**.
- **Universum erweitern:** Standardmäßig ist das EU-Universum begrenzt. Für mehr Breite MDAX/SDAX-Titel in [`config/universe_de.csv`](config/universe_de.csv) ergänzen.
- **US-Backtest gekappt:** Der US-Backtest verarbeitet aus Laufzeitgründen nur die ersten **500 Titel** (`scripts/run_backtest.py`). Beim Ausweiten des US-Universums diese Grenze berücksichtigen.
- **Score-Gewichte nachkalibrieren:** Nach **4–8 Wochen Paper-Trading** die Signalqualität anhand der protokollierten Trades in `state/history/trades_*.csv` auswerten und die Score-Gewichte entsprechend nachjustieren.

---

*TrainSpotter — Analyse, keine Anlageberatung.*
