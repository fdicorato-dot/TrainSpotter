# TrainSpotter 🚂 — Design-Dokument

**Datum:** 2026-07-07
**Status:** Vom Nutzer freigegebenes Design (Teile 1–5 einzeln bestätigt)
**Nutzer:** Ferdinando Dicorato
**Geplant mit:** Claude Fable 5 · **Umsetzung durch:** Claude Opus

---

## 1. Idee und These

**These des Nutzers:** Aktien, die eine starke Aufwärtsbewegung beginnen („der fahrende Zug"), setzen diese Bewegung mit erhöhter Wahrscheinlichkeit kurzfristig fort. Statt Tiefpunkte vorherzusagen, wird bestätigtes Momentum erkannt und die Bewegung mitgefahren. Das entspricht der akademisch belegten Strategiefamilie Momentum-/Breakout-Trading (relative Stärke, Gap-and-Go).

**Kern-Anforderung Latenz:** Ein Trainspotter sieht den Zug **beim Anfahren**, nicht 40 Minuten später. Die Erkennungslatenz ist der Kern der Strategie. Ziel-Latenz: **2–5 Minuten** für US-Titel (Echtzeitdaten), ~15–20 Minuten für DE/EU (verzögerte Gratis-Daten).

**Realismus-Vereinbarung:** „Min. 10 % pro Trade" ist nur bei hochvolatilen Titeln erreichbar und dort mit entsprechendem Verlustrisiko verbunden. Deshalb Hybrid-Ansatz mit zwei getrennten Listen (siehe §4). Erwartbare Trefferquote bei Breakout-Strategien: 40–55 %; die Strategie funktioniert nur mit konsequentem Stop-Loss (klein verlieren, groß gewinnen). Trades ohne Stop-Loss gibt es im System nicht.

## 2. Vom Nutzer getroffene Entscheidungen

| Frage | Entscheidung |
|---|---|
| Rendite-/Risikoprofil | **Hybrid: zwei Listen** (konservativ 2–5 %, spekulativ 10 %+) |
| Markt | **US (NYSE/NASDAQ) + DE/EU (DAX/MDAX/SDAX/TecDAX)** |
| Lieferform | **Laufender Scanner mit Push-Alerts bei Zug-Erkennung, via Telegram** (WhatsApp verworfen: Business-API kostenpflichtig) |
| Umfang | **Alerts + Paper-Trading-Tracking** (Validierung vor Echtgeld) |
| Betrieb | **GitHub Actions (Cloud, kostenlos)** |
| Erkennungsmethode | **Hybrid: regelbasierter Scanner + KI-Bewertung pro Treffer** |
| KI-Kosten | **Null:** `claude-code-action` mit Abo-Token (`claude setup-token`) statt API-Schlüssel — läuft über das bestehende Claude-Abo des Nutzers |
| Repo-Sichtbarkeit | **Öffentlich** (unbegrenzte kostenlose Actions-Minuten für den Dauerbeobachter; Secrets bleiben geheim) |

## 3. Gesamtarchitektur

Fünf Bausteine, alle orchestriert über GitHub Actions in einem öffentlichen Repo:

```
1. NACHT-SCAN            1× täglich ~07:00 MEZ (Cron-Job)
   Ganzes Universum (~7000 US + ~160 DE) → Watchlist ~150 Titel
   („Wer steht heute am Bahnsteig?"), vorsortiert konservativ/spekulativ

2. LIVE-BEOBACHTER       Dauerjob je Marktsitzung (long-running Actions-Job)
   EU-Sitzung 09:00–17:30 MEZ · US-Sitzung 15:30–22:00 MEZ
   Rollierende Kursabfrage der Watchlist + Tages-Topmover
   → Trigger-Erkennung („Der Zug fährt an!")

3. KI-BEWERTUNG          claude-code-action (Abo-Token), nur bei Triggern
   Input: Chartdaten-Zusammenfassung + aktuelle Schlagzeilen
   Output: Score-Bestätigung, Katalysator, Risiken, 2 Sätze Begründung

4. TELEGRAM-BOT          Alerts, Morgen-Depesche, Positions-Updates,
                         Abend-Bilanz, Kommandos /status und /stats

5. PAPER-TRADING-BUCH    Dateien im Repo (CSV/JSON), vom Job committet;
                         virtuelle Trades nach festen Regeln verwaltet
```

**Warum zweistufig (Nacht-Scan → Live-Beobachter):** 7000 Titel im Minutentakt sprengen jedes Gratis-API-Limit. Züge, die anfahren, standen fast immer vorher „am Bahnsteig" (Volumenaufbau, nahe Widerstand) — der Nacht-Scan findet sie, der Live-Beobachter muss nur noch ~150 Titel eng überwachen.

**Technik:** Python + pandas. Zustand (Watchlist, offene Positionen, Historie, bereits gemeldete Alerts) als versionierte Dateien im Repo — keine externe Datenbank, kein Server. Die Datenschicht ist ein eigenes Modul mit austauschbaren Quellen (yfinance ist inoffiziell und kann brechen).

**Laufende Kosten: 0 €.** Actions-Minuten unbegrenzt (öffentliches Repo), Daten kostenlos, KI über bestehendes Abo, Telegram-Bot-API kostenlos.

## 4. Die zwei Listen

| | **Konservativ** | **Spekulativ** |
|---|---|---|
| Zielgewinn | 2–5 % pro Trade | min. 10 % pro Trade |
| Universum | liquide Mid/Large Caps | volatile Small Caps, Gapper, News-Titel |
| ADR-Anforderung (Ø-Tagesspanne) | ≥ 1,5 % | ≥ 3 % |
| Stop-Loss | ca. −3 % (unter Ausbruchsniveau) | ca. −6 % (unter Ausbruchsniveau) |
| Ziel 1 | +4 % | +10 % |
| Übernacht | erlaubt, max. 3 Handelstage | **nie** — Schluss zum Handelsende (Gap-Risiko) |
| „Zug verpasst"-Grenze | Kurs > +4 % über Ausbruch | Kurs > +6 % über Ausbruch |

## 5. Datenquellen (alle kostenlos)

| Quelle | Nutzung | Grenzen |
|---|---|---|
| **yfinance** (Yahoo, inoffiziell, kein Key) | Tagesdaten mit Jahren Historie (Nacht-Scan, Backtest); Intraday-Kerzen als Tageskontext; DE-Titel via `.DE`-Suffix; Sammel-Downloads für Universums-Scan; News-Schlagzeilen | Intraday ~15 Min. verzögert; inoffizielle API kann sich ändern → Datenschicht austauschbar bauen; Intraday-Historie nur ~60 Tage |
| **Finnhub** (Gratis-Tier, API-Key) | **Echtzeitkurse US** (60 Abfragen/Min → Watchlist rollierend, jeder Titel alle 2–3 Min); Unternehmens-News für KI-Bewertung; Ausweichquelle | Echtzeit nur US; EU-Echtzeit gibt es gratis nicht |
| **NASDAQ Trader Symbol-Listen** | US-Universum (~7000 Titel), täglich aktualisiert, frei abrufbar | — |
| **Gepflegte Liste im Repo** | DE/EU-Universum: DAX+MDAX+SDAX+TecDAX (~160 Titel) | manuell zu pflegen (selten nötig) |

**Konsequenz der Datenlage:** US ist das Hauptgleis für schnelle 10-%-Züge (Echtzeit). DE/EU läuft mit ~15 Min. Verzögerung mit — geeignet für die gemächlicheren konservativen Züge, ungeeignet für Minuten-Timing. Das wird im Alert transparent gemacht.

**Vorbörse:** US-Pre-Market-Daten sind gratis nur eingeschränkt verfügbar; der Beobachter nutzt zu US-Öffnung Vortagesschluss + verfügbare Finnhub-Indikationen.

## 6. Zugerkennung

### 6.1 Stufe 1 — Nacht-Scan: Bahnsteig-Score

Universum wird zunächst hart vorgefiltert: Mindestpreis $2 / 2 €, Mindest-Dollarvolumen ~$5 Mio/Tag (Handelbarkeit; keine toten Pennystocks). Danach Punktevergabe:

| Kriterium | Messung | Bedeutung |
|---|---|---|
| Druck im Kessel | Volumen der letzten 3–5 Tage ≥ 1,5× 20-Tage-Schnitt | Käufer positionieren sich |
| Nahe der Abfahrt | Kurs < 5 % unter Widerstand (20-Tage-Hoch bzw. 52-Wochen-Hoch) | kurz vor dem Signal |
| Gleis frei | Kurs > SMA20 und SMA50, beide steigend | Aufwärtstrend intakt; nie auf Züge Richtung Süden springen |
| Relative Stärke | Aktie schlägt ihren Referenzindex über 1–3 Monate | Momentum-Effekt |
| Beweglichkeit | ADR ≥ 1,5 % (konservativ) / ≥ 3 % (spekulativ) | historisch bewegungsfähig |

Ergebnis: **Bahnsteig-Score** je Titel; die besten ~150 bilden die Tages-Watchlist, jeder Titel mit vorgemerktem **Ausbruchsniveau** und Listenzuordnung. Exakte Punktgewichte werden im Implementierungsplan festgelegt und per Backtest kalibriert.

### 6.2 Stufe 2 — Live-Trigger

Alert genau dann, wenn bei einem Watchlist-Titel **alle** Bedingungen gleichzeitig gelten:

1. **Ausbruch:** Kurs überschreitet das vorgemerkte Ausbruchsniveau.
2. **Mit Volumen:** aufgelaufenes Tagesvolumen ≥ ~2× des zeitanteiligen 20-Tage-Durchschnitts (zeitanteilig = auf die Uhrzeit normiert). Ausbruch ohne Volumen = Geisterzug, kein Alert.
3. **Nicht schon abgefahren:** Kurs max. +4 % (konservativ) / +6 % (spekulativ) über Ausbruchsniveau — darüber Meldung „Zug verpasst" statt Einstiegsempfehlung.
4. **Markt-Rückenwind:** Referenzindex (S&P 500 / DAX) intraday nicht < −1,5 %; sonst nur noch spekulative Alerts mit ausdrücklichem Warnhinweis.

Zusätzlich beobachtet der Live-Beobachter die **Tages-Topmover** (Yahoo-Screener) als zweite Quelle — Züge, die der Nacht-Scan nicht auf dem Zettel hatte (Overnight-News), durchlaufen dieselben Trigger-Bedingungen mit ad hoc berechnetem Ausbruchsniveau.

### 6.3 KI-Bewertung (pro Trigger)

`claude-code-action` (Abo-Token als Repo-Secret) erhält: Regel-Treffer + Kursdaten-Zusammenfassung + jüngste Schlagzeilen (Finnhub/Yahoo). Sie liefert strukturiert: Katalysator ja/nein und welcher, Gegenargumente/Risiken, Bestätigung der Listenzuordnung, zwei Sätze Begründung für den Alert. Die KI kann einen Alert **abwerten, aber keinen erfinden** — Regeln bleiben die Quelle der Wahrheit.

### 6.4 Alert-Inhalt

Ticker, Liste, Regel-Begründung (welche Kriterien, mit Zahlen), KI-Einschätzung, **Einstieg** (aktueller Kurs), **Stop-Loss** (unter Ausbruchsniveau, §4), **Ziel 1**, Trailing-Regel für den Rest. **Kein Alert ohne Stop-Loss — ohne Ausnahme.**

### 6.5 Alert-Disziplin

Max. ~5 Alerts pro Liste pro Tag (beste nach Score), max. 1 Alert pro Ticker pro Tag (dedupliziert über Alert-ID = Ticker+Datum, persistiert im Repo-Zustand). Ein Bot, der 30× täglich klingelt, wird stummgeschaltet und ist wertlos.

## 7. Paper-Trading-Buch

- **Eröffnung:** jeder Alert wird automatisch virtueller Trade; Einstieg = Alert-Kurs **+ 0,2 % Malus** (Spread/Slippage — perfekte Ausführung anzunehmen wäre Selbstbetrug).
- **Positionsgröße:** einheitlich 1.000 € virtuell pro Trade (Vergleichbarkeit).
- **Verwaltung (fest, ausnahmslos):** Stop erreicht → schließen, Verlust verbuchen. Ziel 1 erreicht → halbe Position verbuchen, Rest mit Trailing-Stop (nachgezogen unter das Tief der letzten ~30 Min). Spekulativ: Zwangsschluss zum Handelsende. Konservativ: max. 3 Handelstage.
- **Persistenz:** CSV/JSON im Repo, vom Job committet. Je Trade: Zeitstempel, Ticker, Liste, Bahnsteig-Score, ausgelöste Regeln (!), KI-Score, Ein-/Ausstieg, Ergebnis. Die Regel-Herkunft je Trade ermöglicht später die Analyse, welche Kriterien Treffer produzieren und welche Lärm.
- **Erfolgsmessung:** nach 4–8 Wochen Trefferquote, Ø-Gewinn/-Verlust, Profit-Faktor — **getrennt je Liste**. Echtgeld ist erst danach ein Thema, und nur bei positiven Zahlen.

## 8. Telegram-Bot

| Nachricht | Wann | Inhalt |
|---|---|---|
| 🚂 Zug-Alert | sofort bei Trigger | §6.4 |
| 📋 Morgen-Depesche | ~08:45 MEZ | heutige Watchlist, je Titel eine Zeile mit Ausbruchsniveau |
| 🔔 Positions-Update | bei Ereignis | Ziel erreicht / Stop gerissen / Trailing nachgezogen / Zwangsschluss |
| 📊 Abend-Bilanz | ~22:15 MEZ | Tages-P&L Paper-Trading, offene Positionen, Gesamtstatistik je Liste, Disclaimer |

Kommandos: `/status` (offene Positionen + heutige Alerts), `/stats` (Gesamtstatistik). Mehr Interaktivität bewusst nicht in V1 — der Bot ist Melder, nicht Chatpartner. Morgen-Depesche und Abend-Bilanz kommen **immer** (Herzschlag-Prinzip, §10).

## 9. Backtest & Validierung

- **Tages-Backtest über 3–5 Jahre** (kostenlose Tagesdaten): Nacht-Scan für jeden historischen Tag simulieren; messen, wie Bahnsteig-Kandidaten nach Überschreiten des Ausbruchsniveaus in den folgenden 1–5 Tagen liefen. Tausende Fälle, inkl. schlechter Marktphasen (z.B. 2022). Beantwortet: hat das Muster einen statistischen Vorteil? Kalibriert außerdem die Score-Gewichte.
- **Grenze:** minutengenaue Trigger sind mangels langer Gratis-Intraday-Historie (~60 Tage) nicht über Jahre rückrechenbar → das validiert das **Paper-Trading als Live-Test** (Timing, Slippage, Trailing).
- **Backtest bleibt als Werkzeug:** jede spätere Regeländerung wird erst rückgerechnet, dann live geschaltet.
- **Trockenlauf-Modus:** Gesamtsystem durchläuft mit aufgezeichneten Daten einen simulierten Handelstag, bevor es je live geht.

## 10. Fehlerfälle & Betrieb

| Störung | Verhalten |
|---|---|
| Datenquelle antwortet nicht | Retries mit Backoff; bei längerem Ausfall Telegram-Warnung „⚠️ Scanner fährt blind" |
| Ticker liefert Datenmüll | überspringen + loggen; ein kranker Ticker stoppt nie den Scan |
| Actions-Job stirbt | Herzschlag-Prinzip (ausbleibende Depesche/Bilanz = Systemausfall sichtbar); automatischer Neustart des Session-Jobs |
| Doppel-Alerts nach Neustart | Alert-ID (Ticker+Datum) im versionierten Zustand; nie doppelt melden |
| Zustandsdatei beschädigt | Plausibilitätsprüfung vor jedem Schreiben; Git-Historie als Wiederherstellung |
| Feiertage/Wochenende | Börsenkalender (US + DE getrennt); keine unnötigen Läufe |

**GitHub-Actions-Realitäten:** Cron-Starts können 3–15 Min. verzögern (für Nacht-Scan egal; Session-Jobs starten mit Puffer vor Börsenöffnung). Job-Limit 6 h → US-Sitzung (6,5 h) in zwei überlappende Jobs geteilt oder Job startet sich selbst neu.

## 11. Qualitätssicherung

- **Unit-Tests** für alle Indikator-Berechnungen (Volumen-Ratio, relative Stärke, ADR, Ausbruchsniveaus, zeitanteiliges Volumen) mit von Hand nachgerechneten Erwartungswerten — ein Vorzeichenfehler wäre sonst wochenlang unsichtbar.
- **Integrationstest** = Trockenlauf-Modus (§9) mit aufgezeichneten Daten.
- **Disclaimer** in jeder Abend-Bilanz: Analyse, keine Anlageberatung. Paper-Trading-Phase ist bewusst vor jede Echtgeld-Entscheidung geschaltet.

## 12. Nicht-Ziele (V1)

- **Keine Orderausführung / Broker-Anbindung** — das System analysiert und meldet; gehandelt wird manuell (Architektur schließt spätere Anbindung nicht aus).
- **Kein Sekunden-Scalping** — Latenz 2–5 Min. (US) ist Designgrenze der Gratis-Daten.
- **Kein Machine-Learning-Modell** — bewusst verworfen (Blackbox, Überanpassung); Regeln + KI-Bewertung.
- **Kein WhatsApp** — Business-API kostenpflichtig; Telegram gewählt.
- **Keine Krypto** — kann später als eigenes Modul folgen.
- **Kein interaktiver Chat-Bot** — Telegram-Bot ist Melder mit zwei Kommandos.

## 13. Offene Punkte für den Implementierungsplan

- Exakte Score-Gewichte des Nacht-Scans (per Backtest kalibrieren, Startwerte im Plan festlegen)
- Aufteilung der US-Sitzung auf Actions-Jobs (2 überlappende vs. Selbst-Neustart)
- Genaues Datenformat der Zustands-/Historien-Dateien
- Telegram-Bot-Einrichtung (BotFather-Token, Chat-ID) und `claude setup-token` — einmalige manuelle Schritte des Nutzers, im Plan als Checkliste
