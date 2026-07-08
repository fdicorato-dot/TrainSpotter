# TrainSpotter — Tiefenreview (Fable 5)

**Datum:** 2026-07-08 · **Reviewer:** Claude Fable 5 (Senior-Review, read-only)
**Gegenstand:** Kompletter Code (`trainspotter/`, `scripts/`, `tests/`, `.github/workflows/`), Spec (`docs/superpowers/specs/2026-07-07-trainspotter-design.md`), Plan (`docs/superpowers/plans/2026-07-08-trainspotter.md`), erster Live-State (`state/watchlist.json` vom 08.07.).
**Charakter:** Verbesserungsreview, kein Bug-Hunt. Nichts wurde verändert, nichts committet.

**Gesamteindruck vorweg:** Der Code ist für ein von Subagenten gebautes System ungewöhnlich diszipliniert — kleine Module, injizierte Abhängigkeiten (`Deps`), atomare State-Writes, saubere Degradation der KI-Bewertung, gute Golden-Tests. Die Findings unten sind überwiegend Strategie-Verzerrungen und Dauerbetriebs-Themen, keine strukturellen Mängel.

**Findings:** Kategorie 1 (Strategie): 10 · Kategorie 2 (Robustheit): 9 · Kategorie 3 (Codequalität): 8 · Kategorie 4 (Performance): 4 · Kategorie 5 (Live-Daten): 4 — **gesamt 35**.

---

## Prioritätenliste (sortiert nach Nutzen/Aufwand)

| # | Finding | Aufwand | Nutzen |
|---|---|---|---|
| 1.1 | U-Kurven-Problem: lineare Volumen-Proration macht den Volumen-Filter morgens wirkungslos | S–M | **hoch** |
| 5.1 | Globale Watchlist-Kappung: Cut im Score-65-Tie ist rein **alphabetisch**, EU strukturell verdrängt | S–M | **hoch** |
| 1.2 | `intraday_snapshot` prüft nicht, ob die Bars von **heute** sind → Vortagsvolumen zur Öffnung → Falschtrigger | S | **hoch** |
| 1.7 | „Zug verpasst"-Meldungen sind unbudgetiert → Topmover-Quelle kann bis zu 25 Missed-Meldungen/Tag erzeugen | S | **hoch** |
| 4.1 | Nacht-Scan lädt 2 Jahre Historie, braucht ~80 Tage → `period="6mo"` spart ~4× Zeit/RAM/Transfer | S | **hoch** |
| 2.1 | Feiertagskalender nur 2026 hartkodiert; keine US-Halbtage → bricht still ab Jan 2027 | S | **hoch** |
| 2.4 | Stiller Totalausfall: per-Ticker-`except` schluckt systematische Fehler; „Scanner fährt blind" feuert dann nie | S | **hoch** |
| 2.5 | Kein Logging — leeres Actions-Log macht „warum kein Alert?" undiagnostizierbar | M | **hoch** |
| 1.4 | Backtest validiert eine **andere** Strategie als live läuft (kein Volumen-Trigger, kein Indexfilter, kein Budget) | M | **hoch** |
| 3.1 | Fehlende load-bearing Tests: `run_session`, `build_deps`, `poll_commands` | M | hoch |
| 1.9 | Risiko-Asymmetrie: reales Risiko spekulativ bis ~12 % statt 6 % bei fixer 1000-€-Größe | S | mittel |
| 1.3 | Volumen-Staleness (15-Min-Delay + 5-Zyklen-Cache) vs. aktueller `elapsed_frac` → Ratio mittags unterschätzt | S | mittel |
| 1.6 | `auto_adjust=True` vs. Finnhub-Rohkurse: Split/Dividende verschiebt Level; kein Preis-Sanity-Check | S | mittel |
| 5.3 | DE-Universum nur 51 Titel statt ~160 laut Spec | S | mittel |
| 5.2 | 121/150 spekulativ: plausibel, aber schief zum 5er-Alert-Budget je Liste | S | mittel |
| 2.2 | DST: UTC-Crons verbrennen im Winter ~1 h Job-Budget im Warte-Loop | S | mittel |
| 4.3 | Finnhub-Budget am Limit (~3 min/Zyklus); adaptive Priorisierung halbiert Latenz für heiße Titel | M | mittel–hoch |
| 1.5 | Survivorship-Bias im Backtest (heutiges Universum, `[:500]` alphabetisch) | M | mittel |
| übrige | siehe Kategorien unten | S | gering–mittel |

---

## Kategorie 1 — Strategie-Korrektheit (10 Findings)

### 1.1 U-Kurven-Hypothese: **bestätigt** — lineare Volumen-Proration überschätzt das Ratio am Morgen massiv
**Code:** `trainspotter/indicators.py:30-33` (`time_prorated_volume_ratio`: `expected = avg_daily_volume * max(elapsed_frac, 0.05)`), genutzt in `trainspotter/triggers.py:9-11` gegen `cfg.TRIGGER_VOL_RATIO = 2.0` (`trainspotter/config.py:21`).

Die Proration ist strikt linear in der Sitzungszeit (`calendar_utils.py:21-25`). Reales US-Aktienvolumen ist U-förmig: In der ersten Handelsstunde (15 % der Sitzungszeit) laufen typisch 25–35 % des Tagesvolumens auf (inkl. Opening Auction), mittags kommt fast nichts, zum Schluss wieder viel. Konsequenz, konkret durchgerechnet:

- 10:00 ET (`elapsed_frac ≈ 0.077`): Ein Titel mit **exakt durchschnittlichem** Tagesverlauf hat bereits ~15–20 % des Tagesvolumens → gemessenes Ratio ≈ **2,0–2,6×** → der Filter ist um die Öffnung herum **faktisch abgeschaltet**. Jeder Ausbruch über das Level triggert, „Geisterzug"-Erkennung existiert morgens nicht.
- Der Floor `max(elapsed_frac, 0.05)` verschärft das in den ersten ~20 Minuten zusätzlich (erwartet nur 5 % des Volumens, real liegen längst >10 % an).
- Spiegelbildlich **unterschätzt** die lineare Kurve das Ratio in der Mittagsflaute — echte Ausbrüche mit relativ starkem Volumen um 12–14 ET können unter 2,0 fallen und werden verpasst.
- Der US-Beobachter startet 15:20 MESZ = 9:20 ET (`.github/workflows/observer-us.yml:4`), also **genau** im überschätzten Fenster. Der Bias trifft die aktivste Phase des Systems.

**Empfehlung:** Statisches kumulatives Intraday-Profil statt Linearität, z. B. Stützstellen `{0.0:0.0, 0.08:0.18, 0.15:0.27, 0.25:0.35, 0.5:0.55, 0.75:0.72, 0.9:0.85, 1.0:1.0}` mit linearer Interpolation (je Markt eine Kurve; EU ist ähnlich U-förmig, flacher am Schluss). Optional später empirisch aus ein paar Wochen 15-Min-Daten kalibrieren. Der Floor kann dann entfallen. Testbar rein in `indicators.py` + `test_indicators.py`.
**Aufwand: S–M · Nutzen: hoch** (der Volumen-Trigger ist laut Spec §6.2 das zentrale Bestätigungskriterium — aktuell misst er morgens Rauschen).

### 1.2 `intraday_snapshot` prüft nicht, ob die gelieferten Bars vom heutigen Tag sind
**Code:** `trainspotter/data/yahoo.py:31-41` — `yf.download(period="1d", interval="15m")`, dann `day_volume = sub["Volume"].sum()`.

`period="1d"` liefert den **letzten verfügbaren Handelstag**. Unmittelbar nach Börsenöffnung (oder wenn Yahoo hakt) sind das die kompletten Bars von **gestern**. Dann gilt: `day_volume` = volles Gestern-Volumen, `elapsed_frac ≈ 0` → Floor 0,05 → Ratio ≈ 20× → jeder Titel knapp überm Level erzeugt sofort einen Falsch-Alert. Zusammen mit 1.1 ist die Öffnungsphase doppelt anfällig. Betrifft auch die EU-Quotes (dort ist der Snapshot die einzige Preisquelle — ein Gestern-Schlusskurs würde als Live-Preis behandelt).

**Empfehlung:** Bars auf das lokale Handelsdatum filtern (`sub.index[-1].date() == heute` bzw. nur Zeilen von heute summieren); liefert Yahoo nichts von heute → Ticker in diesem Zyklus auslassen.
**Aufwand: S · Nutzen: hoch.**

### 1.3 Volumen-Staleness: Cache + Yahoo-Delay vs. aktueller Zeitanteil
**Code:** `trainspotter/live_observer.py:172-181` (Refresh nur alle `US_VOLUME_REFRESH_CYCLES = 5` Zyklen, `config.py:37`), Yahoo-Intraday zusätzlich ~15 Min verzögert.

Ein US-Zyklus dauert real ~3 Min (siehe 4.3) → das Volumen ist bis zu ~15 Min Cache + 15 Min Delay = **30 Min alt**, wird aber gegen den **aktuellen** `elapsed_frac` normiert (`triggers.py:9`). Mitten am Tag unterschätzt das das Ratio um bis zu ~10–15 % — systematisch, immer in Richtung „Trigger verpassen". Genau der Fall „Ausbruch beim Anfahren erkennen" (Spec §1) leidet: Der Preis ist Echtzeit (Finnhub), das bestätigende Volumen hinkt.

**Empfehlung:** Beim Snapshot den Zeitstempel des letzten Bars mitspeichern und `elapsed_frac` auf **diesen** Zeitpunkt beziehen; alternativ Erwartungswert um (Cache-Alter + 15 Min) korrigieren.
**Aufwand: S · Nutzen: mittel.**

### 1.4 Der Backtest validiert eine andere Strategie als die, die live läuft
**Code:** `trainspotter/backtest.py:5-28`.

- **Kein Volumen-Trigger:** `simulate_trade` steigt ein, sobald `High > level` — die Live-Kernbedingung `vol_ratio ≥ 2.0` (`triggers.py:10`) fehlt komplett, obwohl Tagesvolumen im Daily-DF vorhanden wäre (mindestens als „Tagesvolumen ≥ 1,5–2× 20-Tage-Schnitt"-Proxy prüfbar).
- **Kein Indexfilter** (`triggers.py:13-16` hat keine Backtest-Entsprechung).
- **Kein Alert-Budget / keine Priorisierung:** live max. 5/Liste/Tag (`apply_alert_discipline`), im Backtest zählt jeder Kandidat → Backtest-Kennzahlen (Trefferquote, PF) sind nicht auf das Live-System übertragbar.
- **„Missed"-Grenze hart 4 %:** `backtest.py:8` nutzt `level * 1.04` für beide Listen; live gilt 4 %/6 % je Liste (`config.py:23`).
- Positiv: kein Look-ahead — `platform_score` läuft auf `df.iloc[:t+1]`, gehandelt wird `t+1` (`backtest.py:50-52`); Stop-vor-Ziel-Pessimismus bei Doji-Tagen ist dokumentiert (`backtest.py:18`); Index-Alignment-Guard (`backtest.py:39-43`) ist korrekt.

**Empfehlung:** Volumen-Proxy-Trigger + Indexfilter + listenspezifische Missed-Grenze + Tagesbudget in `simulate` nachziehen, damit „jede Regeländerung wird erst rückgerechnet" (Spec §9) tatsächlich das Live-System rückrechnet.
**Aufwand: M · Nutzen: hoch** (Grundlage jeder späteren Kalibrierung).

### 1.5 Survivorship-Bias im Backtest
**Code:** `trainspotter/universe.py:19-28` (heutige NASDAQ-Symbollisten), `scripts/run_backtest.py:12` (`load_us_universe()[:500]`).

Der 3-Jahres-Backtest sieht nur Titel, die **heute** noch gelistet sind — Delistings (oft die Verlierer genau dieser Strategie: gescheiterte Momentum-Small-Caps) fehlen. Ergebnis wird geschönt. Zusätzlich ist `[:500]` ein alphabetischer Cut (sortiertes Set, `universe.py:28`) — keine Zufallsstichprobe.
**Empfehlung:** Mindestens `random.sample` statt `[:500]` und den Survivorship-Vorbehalt in die Backtest-Ausgabe drucken; sauber wäre eine historische Konstituenten-Quelle (für gratis schwer — dann wenigstens dokumentiert einpreisen, z. B. Trefferquote gedanklich um einige Punkte diskontieren).
**Aufwand: M · Nutzen: mittel.**

### 1.6 Adjustierte Yahoo-Historie vs. Finnhub-Rohkurse — kein Preis-Sanity-Check
**Code:** `trainspotter/data/yahoo.py:24` (`auto_adjust=True`), Level-Berechnung `night_scan.py:20`, Trigger-Vergleich `triggers.py:7`.

Das nächtliche `breakout_level` stammt aus adjustierten Kursen, der Live-Preis (Finnhub `/quote`) ist roh. Dividende im 20-Tage-Fenster → Level minimal zu tief (verfrühte Trigger, klein). Kritischer: **Split über Nacht** → Live-Preis halbiert/vervielfacht sich gegenüber dem Level → garantierter Unsinnstrigger bzw. dauerhaft toter Eintrag.
**Empfehlung:** Plausibilitätsfenster im Trigger: Preis muss z. B. innerhalb ±30 % des letzten Nacht-Scan-Close liegen (Close als Feld in den Watchlist-Eintrag aufnehmen), sonst Ticker für den Tag verwerfen. Nebeneffekt: fängt auch kaputte Quotes ab.
**Aufwand: S · Nutzen: mittel.**

### 1.7 „Zug verpasst" ist unbudgetiert — Topmover-Quelle wird zur Spam-Schleuder
**Code:** `trainspotter/triggers.py:33` (`out = [c for c in fresh if c["status"] == "missed"]` — **alle** Missed passieren ungebremst), `live_observer.py:207-210` (alle 10 Zyklen bis 25 Topmover als Ad-hoc-Einträge).

Tages-Topmover liegen per Definition meist weit über ihrem gestrigen 20-Tage-Hoch → `dist > MISSED_TRAIN_PCT` → Status „missed". Jeder davon erzeugt genau eine Meldung/Tag (Dedup via ID greift), aber bei 25 Movern plus Watchlist-Missed können **>25 „ZUG VERPASST"-Nachrichten pro Tag** auflaufen. Das verletzt den Geist von Spec §6.5 („Ein Bot, der 30× täglich klingelt, wird stummgeschaltet").
**Empfehlung:** Missed-Budget (z. B. max. 3/Tag, beste Scores), und/oder Topmover-Einträge nur dann melden, wenn sie **nicht** sofort missed sind (Mover, der nahe am Ad-hoc-Level konsolidiert, ist die interessante Minderheit).
**Aufwand: S · Nutzen: hoch.**

### 1.8 Spec-Abweichungen im Bahnsteig-Score
**Code:** `trainspotter/night_scan.py:20` und `:31`.

- Spec §6.1: Widerstand = „20-Tage-Hoch **bzw. 52-Wochen-Hoch**" — implementiert ist nur das 20-Tage-Hoch (`BREAKOUT_WINDOW = 20`). Titel knapp unter einem 52-Wochen-Hoch (klassisches Momentum-Setup) mit 20-Tage-Hoch weit darunter bekommen ein zu tiefes, leicht überschreitbares Level.
- Spec §6.1: „Kurs > SMA20 und SMA50, **beide steigend**" — geprüft wird nur die SMA20-Steigung (`sma20.iloc[-1] > sma20.iloc[-6]`), die SMA50-Steigung nicht.

**Empfehlung:** Entweder implementieren oder die Abweichung bewusst in der Spec nachziehen (die 20-Tage-Variante ist vertretbar, sollte aber dokumentierte Entscheidung sein, nicht Zufall).
**Aufwand: S · Nutzen: gering–mittel.**

### 1.9 Risiko-Asymmetrie: fixe Positionsgröße bei stark variablem Stop-Abstand
**Code:** `trainspotter/triggers.py:21-23` (Stop relativ zum **Level**, Einstieg = aktueller Kurs bis +6 % über Level), `paper_trading.py:9` (fix 1000 €).

Spekulativ: Einstieg bis `level*1.06`, Stop `level*0.94` → reales Verlustrisiko bis **~11,7 %** statt der nominellen 6 %. Zwei Trades mit gleichem Setup, aber unterschiedlichem Trigger-Timing haben fast doppelt unterschiedliches Euro-Risiko — das verwässert später die Statistik je Liste (Spec §7 „Vergleichbarkeit").
**Empfehlung:** Entweder Positionsgröße risikonormieren (`qty = RISK_EUR / (entry - stop)`) oder Stop zusätzlich auf `entry * (1 - STOP_PCT)` deckeln. Ersteres ist für die Auswertung sauberer.
**Aufwand: S · Nutzen: mittel.**

### 1.10 Bekannte, akzeptable Vereinfachung: Breakeven statt Trailing im Backtest
**Code:** `trainspotter/backtest.py:24`. Nach Ziel 1 gilt im Backtest ein Breakeven-Stop auf Tagesbasis, live ein 30-Min-Trailing (`paper_trading.py:40-44`). Auf Tagesdaten nicht besser machbar; sollte nur als bekannte Abweichung neben den Backtest-Ergebnissen dokumentiert werden (eine Zeile in der `run_backtest.py`-Ausgabe).
**Aufwand: S · Nutzen: gering.**

---

## Kategorie 2 — Robustheit im Dauerbetrieb (9 Findings)

### 2.1 Kalender nur für 2026 hartkodiert; US-Halbtage fehlen
**Code:** `trainspotter/calendar_utils.py:7-11`.

Ab 2027-01-01 sind die Feiertags-Sets stumm wirkungslos: Jobs laufen an Feiertagen (Datenmüll-Zyklen, sinnlose Actions-Läufe, ggf. „Scanner fährt blind"-Fehlalarme). Der Plan (Backlog Z. 2158) kennt das Wartungsproblem, aber es gibt **keinen technischen Wächter**. Zusätzlich fehlen US-Halbtage (Early Close 13:00 ET, z. B. Tag nach Thanksgiving 27.11.2026, 24.12.): `session_bounds` behauptet 16:00-Schluss → spekulative Positionen bekommen ihren Zwangsschluss erst 3 h nach Handelsende auf eingefrorenen Kursen, und der Job pollt 3 h einen toten Markt.
**Empfehlung:** (a) Guard: `is_trading_day` wirft/warnt per Telegram, wenn `d.year` nicht in den gepflegten Sets vorkommt; (b) `HALF_DAYS`-Set mit 13:00-Schluss ergänzen; (c) mittelfristig `exchange_calendars` als Dependency erwägen.
**Aufwand: S · Nutzen: hoch** (einziger Punkt, der *garantiert* und still bricht — nur eben erst in ~6 Monaten).

### 2.2 DST: UTC-Crons mit MESZ-Annahme
**Code:** `.github/workflows/observer-us.yml:4-5`, `observer-eu.yml:4-5`.

Nach der Umstellung Ende Oktober starten die Jobs 1 h zu früh (Ortszeit): `run_session` wartet dann ~60–70 Min im `sleep(30)`-Loop (`live_observer.py:204-206`) und verbrennt das vom 335-Min-Budget. Durchgerechnet reicht der 2-Teil-Split auch im Winter knapp bis Handelsschluss — es bricht also nichts, aber die Reserve schrumpft auf Minuten (Cron-Verspätungen von 3–15 Min laut Spec §10 fressen den Rest).
**Empfehlung:** Crons je eine Stunde später als zweiten Schedule-Eintrag ergänzen und in `run_session` früh terminieren, wenn die Sitzung bereits von einem laufenden Job abgedeckt ist — oder schlicht die im Plan-Backlog vorgesehene halbjährliche Cron-Pflege in den Kalender des Betreibers. Robusteste Variante: Cron großzügig früh + sofortiges `return`, wenn `now < open_t - 20min`.
**Aufwand: S · Nutzen: mittel.**

### 2.3 `trail_prices` wächst bis Ziel 1 unbegrenzt
**Code:** `trainspotter/paper_trading.py:30` (Append jeden Zyklus), Pruning nur in `_trail_low` (`:22-25`), das erst nach `half_booked` läuft.

Eine konservative Position, die Ziel 1 nie erreicht, sammelt über 3 Handelstage ~300–500 Preis-Tupel, die bei jedem Event-Commit vollständig in `state/positions_*.json` geschrieben und committet werden. Kein Ausfall, aber unnötiges State- und Repo-Wachstum, und `recover_overnight` (`live_observer.py:31`) braucht ohnehin nur den letzten Preis.
**Empfehlung:** In `update_position` immer auf das `TRAIL_WINDOW_MIN`-Fenster prunen (eine Zeile: Pruning aus `_trail_low` an den Anfang von `update_position` ziehen).
**Aufwand: S · Nutzen: gering–mittel.**

### 2.4 Stiller Systemausfall: per-Ticker-`except` maskiert systematische Fehler
**Code:** `trainspotter/live_observer.py:100-101` (`except Exception: continue` je Ticker), Warnung „Scanner fährt blind" nur bei Exception aus `run_cycle` selbst (`:215-218`).

Ändert Yahoo/Finnhub das Antwortformat (z. B. `q["price"]`-KeyError für **alle** Ticker), schluckt der per-Ticker-Catch das komplett: `cands` bleibt für immer leer, `run_cycle` wirft nie, `data_fail` bleibt 0 — das System läuft wochenlang „gesund" und meldet nichts. Das Herzschlag-Prinzip (Spec §10) erkennt tote Jobs, aber nicht blinde.
**Empfehlung:** Fehl-/Leerquote zählen: wenn `quotes` für > x % der Watchlist leer ist oder > x % der Trigger-Checks werfen, einmalig „Scanner fährt blind" senden. Drei Zeilen um `live_observer.py:92-101`.
**Aufwand: S · Nutzen: hoch.**

### 2.5 Kein Logging — Diagnose im Betrieb unmöglich
**Code:** projektweit (`night_scan`, `live_observer`, `yahoo`, `state` — überall `except Exception: continue/pass` ohne jede Ausgabe).

Das Actions-Log eines kompletten Handelstags ist heute **leer**. Die erste Betriebsfrage wird sein: „Warum kam für Ticker X kein Alert?" — unbeantwortbar. Ein `logging`-Setup mit einer Zeile pro Zyklus (n Quotes, n Kandidaten, n gedrosselt, Fehlerzähler) und einer Zeile pro verworfenem Trigger-Grund kostet fast nichts und macht Fehlersuche und spätere Regel-Kalibrierung erst möglich.
**Aufwand: M · Nutzen: hoch.**

### 2.6 `telegram_offset.json` wird von beiden Markt-Jobs geschrieben
**Code:** `trainspotter/live_observer.py:17, 148-160`, `calendar_utils.py:27-30`.

Die Polling-Zeitfenster sind klug disjunkt gemacht (EU pollt nur vor 15:15 Berlin, US ab 15:20) — Doppel-Antworten sind damit ausgeschlossen. Aber beide Jobs committen im Überlappungsfenster 15:20–17:30 auf denselben Branch; ein EU-Commit mit Offset-Änderung um 15:14 kann mit US-Commits kollidieren. `commit_and_push` bricht den Rebase dann sauber ab (`state.py:50-51`) und warnt — Verlustrisiko klein, aber vermeidbar.
**Empfehlung:** Offset-Datei je Markt (`telegram_offset_us.json`/`_eu.json` — Telegram-`getUpdates`-Offsets sind global monoton, ein `max` beim Laden genügt) oder Polling komplett dem US-Job überlassen.
**Aufwand: S · Nutzen: gering.**

### 2.7 Commit-Frequenz an bewegten Tagen
**Code:** `trainspotter/live_observer.py:221-224` — Commit bei **jedem** Zyklus mit Events; „trail"-Events entstehen bei steigendem Kurs praktisch jeden Zyklus (Event wird auch ohne Notification erzeugt, `paper_trading.py:44`).

Eine trailende Position produziert also ~1 Commit/3 Min über Stunden → Dutzende Commits/Tag, jede mit vollem `trail_prices`-Array (siehe 2.3). Kein Limit-Problem, aber Repo-Rauschen und mehr Konfliktfenster (2.6).
**Empfehlung:** Persist/Commit für reine Trail-Events auf z. B. alle 10 Zyklen drosseln; Alerts/Closes weiterhin sofort.
**Aufwand: S · Nutzen: gering.**

### 2.8 EU-Beobachter läuft 8,5 h gegen leere Watchlist
**Code:** `trainspotter/live_observer.py:192-230` — kein Kurzschluss, wenn `watchlist` und `positions` leer sind.

Heutiger Ist-Zustand (0 EU-Titel, siehe 5.1): Der EU-Job pollt einen ganzen Handelstag ins Leere (Yahoo-Snapshots mit leerer Tickerliste, Index-Abfragen, Kommando-Polls). Öffentliches Repo = keine Minutenkosten, aber sinnlose Läufe und irreführende „grüne" Jobs.
**Empfehlung:** Bei leerer Watchlist **und** leeren Positionen: eine Telegram-Notiz („EU heute ohne Kandidaten") und `return`. Wird mit 5.1 zusammen ohnehin seltener.
**Aufwand: S · Nutzen: gering.**

### 2.9 Yahoo-API-Drift: gut gekapselt, aber `yf.screen` ist die fragilste Stelle
**Code:** `trainspotter/data/yahoo.py:51-56`.

Die Kapselung in einem Modul ist genau richtig (Spec §3). `yf.screen("day_gainers")` ist die jüngste/instabilste yfinance-API; ihr Ausfall degradiert still zu `[]` (Topmover-Quelle weg, niemand merkt es). Zusammen mit 2.5: einmal täglich loggen/melden, wenn die Movers-Quelle dauerhaft leer liefert.
**Aufwand: S · Nutzen: gering.**

---

## Kategorie 3 — Codequalität (8 Findings)

### 3.1 Fehlende load-bearing Tests: `run_session`, `build_deps`, `poll_commands`
**Code:** `trainspotter/live_observer.py:162-235`, `telegram_bot.py:45-60`.

Die drei komplexesten Betriebs-Pfade sind ungetestet:
- **`run_session`** (0 Tests): Warte-Loop vor Öffnung, Movers-Merge alle 10 Zyklen, `data_fail`-Eskalation, Split-Verhalten `hard_end` vs. `close_t` (Session-Close darf bei hartem Ende von Teil 1 **nicht** feuern — genau die Invariante, die spekulative Positionen vor Fehl-Schließungen um 18:55 schützt), End-Persist. Testbar mit injiziertem `now_fn` — die Struktur ist da, nur der Loop nutzt `datetime.now` direkt (`:203-204`) statt einer injizierbaren Uhr. Kleiner Refactor (Uhr in `Deps` bzw. Parameter) macht das testbar.
- **`build_deps`** (0 Tests): Die US-Volumen-Cache-Logik (`:172-181`, Refresh-Zyklus, Fallback `day_volume=0.0` wenn Yahoo einen Ticker nicht liefert — 0.0 heißt „nie triggern", das ist eine stille Strategie-Entscheidung!) ist reine Logik und mit zwei Fakes in 20 Zeilen testbar.
- **`poll_commands`** (0 Tests): Offset-Fortschreibung (`max(offset, update_id+1)`), Nicht-Kommando-Filter, kaputtes JSON. Mit `monkeypatch` auf `requests.get` trivial. `_handle_commands` ebenso ungetestet.

**Aufwand: M · Nutzen: hoch** (das sind die Pfade, deren Bruch nicht von bestehenden Tests, sondern erst vom Live-Betrieb entdeckt würde).

### 3.2 `ai_review`: gieriger Regex über die gesamte CLI-Ausgabe
**Code:** `trainspotter/ai_review.py:19` — `re.search(r"\{.*\}", r.stdout, re.S)`.

Greedy von erster `{` bis letzter `}`: Enthält die Claude-Ausgabe zwei JSON-Blöcke oder eine geschweifte Klammer im Fließtext hinter dem JSON, schlägt `json.loads` fehl → KI-Einschätzung fällt still aus (degradiert korrekt, aber unnötig oft).
**Empfehlung:** `claude -p --output-format json` verwenden (strukturierte Hülle, `result`-Feld parsen) oder mehrere Kandidaten-Matches non-greedy durchprobieren.
**Aufwand: S · Nutzen: gering–mittel.**

### 3.3 `poll_commands` filtert nicht nach Chat-ID
**Code:** `trainspotter/telegram_bot.py:54-59`.

Jeder, der den (öffentlich auffindbaren) Bot anschreibt, kann `/status`/`/stats` auslösen. Die Antworten gehen an die konfigurierte `TELEGRAM_CHAT_ID` — kein Datenleck, aber Fremde können euren Chat mit Status-Antworten fluten. Ein Vergleich `u["message"]["chat"]["id"] == TELEGRAM_CHAT_ID` genügt.
**Aufwand: S · Nutzen: gering.**

### 3.4 Duplikat: Watchlist-Eintragsbau in `movers_entries` vs. `platform_score`
**Code:** `trainspotter/live_observer.py:66-71` vs. `night_scan.py:40-42`.

Zwei Stellen bauen dieselbe Eintragsstruktur (Feld-Drift-Gefahr: ein neues Feld im Nacht-Scan-Eintrag, z. B. der `last_close` aus 1.6, würde bei Movers fehlen und im Trigger `KeyError` werfen — der dann still geschluckt würde, siehe 2.4). Gemeinsamen Konstruktor `make_entry(...)` extrahieren.
**Aufwand: S · Nutzen: gering.**

### 3.5 Totes Feld: `"entry"` dupliziert `"price"` im Trigger-Resultat
**Code:** `trainspotter/triggers.py:21` — `"price": price, "entry": price`. Eines von beiden reicht (`open_position` nutzt `entry`, die Formate `price`). Kosmetik, aber es suggeriert eine Unterscheidung, die es nicht gibt.
**Aufwand: S · Nutzen: gering.**

### 3.6 Telegram-Send: Retries ohne Backoff, 429 unbehandelt
**Code:** `trainspotter/telegram_bot.py:32-42` — drei sofortige Versuche; ein `retry_after` aus einer 429-Antwort (bei Missed-Wellen aus 1.7 realistisch) wird ignoriert und `r.ok=False` verbrennt alle Versuche in <1 s.
**Empfehlung:** kleiner `time.sleep(2**i)` und 429-`retry_after` respektieren.
**Aufwand: S · Nutzen: gering.**

### 3.7 Mindesthistorie 60 vs. `RS_DAYS = 60`
**Code:** `trainspotter/night_scan.py:6` (`len(df) < 60` → raus) vs. `indicators.py:20-21` (`relative_strength` braucht `days+1 = 61` Punkte, liefert sonst still `0.0`).

Titel mit exakt 60 Zeilen (junge IPOs — oft genau die spannenden Momentum-Kandidaten) passieren den Längen-Check, verlieren aber kommentarlos bis zu 20 RS-Punkte. Grenze auf `cfg.RS_DAYS + 1` heben oder RS bei zu kurzer Historie als „nicht bewertbar" von „0 Outperformance" unterscheiden.
**Aufwand: S · Nutzen: gering.**

### 3.8 `split_batch`: Nicht-MultiIndex-Pfad ordnet dasselbe DF jedem Ticker zu
**Code:** `trainspotter/data/yahoo.py:12` — bei flachen Spalten (yfinance liefert das, wenn nur **ein** Ticker Daten hat) bekommt **jeder** angefragte Ticker `sub = df`. Fragt man 3 Ticker an und nur einer liefert, erhalten alle 3 dieselben Kurse. Selten, aber im Movers-Pfad (kleine `fresh`-Listen) realistisch.
**Empfehlung:** Im Nicht-MultiIndex-Fall nur zuordnen, wenn `len(tickers) == 1`.
**Aufwand: S · Nutzen: gering (aber ein echter Korrektheits-Splitter).**

---

## Kategorie 4 — Performance (4 Findings)

### 4.1 Nacht-Scan lädt 2 Jahre Historie — gebraucht werden ~80 Tage
**Code:** `trainspotter/data/yahoo.py:19` (`period="2y"` als Default), `scripts/run_night_scan.py:27`.

`platform_score` schaut maximal 61 Handelstage zurück (RS 60, Volumen 25, SMA50). 2 Jahre × 7000 Titel sind ~3,5 Mio Zeilen umsonst — Laufzeit, Yahoo-Last (Rate-Limit-/Blockrisiko!) und RAM je ~4× höher als nötig. `period="6mo"` (~126 Handelstage) lässt komfortable Reserve.
**Aufwand: S · Nutzen: hoch** (größter Einzelhebel für den Nacht-Scan; senkt auch das Risiko, dass Yahoo den Runner drosselt und der Scan Kandidaten verliert).

### 4.2 Nacht-Scan hält alle 7000 DataFrames gleichzeitig im Speicher
**Code:** `trainspotter/data/yahoo.py:19-29` (sammelt alles in `out`), `scripts/run_night_scan.py:10-17` (scort erst danach).

Peak-RAM heute grob 0,5–1,5 GB (mit 2y-Historie). Auf dem 7-GB-Runner tragbar, aber unnötig: pro 400er-Batch scoren und die DFs verwerfen (Generator-Variante von `daily_history` oder Score-Callback) drückt den Peak auf ~100 MB und beschleunigt durch weniger GC-Druck. Zusammen mit 4.1 umsetzen.
**Aufwand: S–M · Nutzen: mittel.**

### 4.3 Finnhub-Budget: Zyklus ~3 Min bei 150 Titeln — Latenzziel gerade so erfüllt, ohne Reserve
**Code:** `trainspotter/data/finnhub.py:13-15` (1,05 s/Call), `live_observer.py:82-83` (alle Watchlist- + Positions-Ticker jeden Zyklus), `config.py:36`.

Rechnung: 150 × 1,05 s ≈ 158 s + 15 s Sleep + alle 5 Zyklen Yahoo-Snapshot (~20–40 s) + Movers alle 10 Zyklen → **Zyklus ~3 Min**, Erkennungslatenz im Mittel ~1,5 Min, worst case ~3+ Min. Spec-Ziel 2–5 Min: erfüllt, aber jede Watchlist-Vergrößerung (Movers addieren bis 25) schiebt Richtung Obergrenze.
**Empfehlung:** Adaptive Priorisierung: Ticker, deren letzter Preis > 5 % **unter** dem Level lag, nur jeden 2.–3. Zyklus quoten; Titel nahe am Level und offene Positionen jeden Zyklus. Halbiert die effektive Latenz für die heißen Titel und schafft Luft für Movers. Alternative Eskalation (später): Finnhub-Websocket (im Gratis-Tier enthalten) für die Top-30.
**Aufwand: M · Nutzen: mittel–hoch.**

### 4.4 Movers-Historienabruf mit 2-Jahres-Default
**Code:** `trainspotter/live_observer.py:59` ruft `yahoo.daily_history(fresh)` mit `period="2y"`-Default — mitten in der Sitzung, im Beobachter-Loop. Für ein Ad-hoc-Level reichen 3 Monate; `period="3mo"` übergeben.
**Aufwand: S · Nutzen: gering.**

---

## Kategorie 5 — Erste Live-Daten: `state/watchlist.json` (4 Findings)

### 5.1 Die globale Kappung ist in dieser Form eine Fehlkonstruktion — der Cut ist nachweislich **alphabetisch**
**Code:** `trainspotter/night_scan.py:44-45` (`sorted(..., key=score, reverse=True)[:150]`), `scripts/run_night_scan.py:8` (US wird vor EU gescort), `universe.py:28` (Universum alphabetisch sortiert).

Befund aus dem Live-State (150 Einträge): Score-Verteilung `{65: 137, 70: 5, 90: 8}`, 0 EU-Titel. Die 137 Einträge mit Score 65 sind **strikt alphabetisch geordnet und enden bei „O"** (…NVCT, ODD, OKTA). Beweiskette: Pythons `sorted` ist stabil → bei Score-Gleichstand bleibt die Einfügereihenfolge = alphabetische US-Reihenfolge, dann EU. Es gab also ≥137 weitere Kandidaten mit Score 65 (alles ab „P" im US-Alphabet plus sämtliche EU-65er), die **ausschließlich wegen ihres Anfangsbuchstabens bzw. ihrer Marktreihenfolge** herausfielen. Die Watchlist-Zusammensetzung unterhalb Score 70 ist heute arbiträr, nicht qualitätsbasiert; die EU-Schiene ist strukturell tot (ihr Beobachter lief 8,5 h gegen eine leere Liste, siehe 2.8).

Zwei unabhängige Ursachen, beide beheben:
1. **Score zu grob:** Nur 5 diskrete Kriterien in 10/20/25-Punkte-Sprüngen → Massen-Ties. Fix: kontinuierlicher Tiebreaker im Sortierschlüssel, z. B. `(score, rs_pp, vol_buildup_ratio, -abs(dist))` — die Rohwerte liegen in `platform_score` bereits vor (`night_scan.py:25-37`) und müssten nur ins Ergebnis-Dict.
2. **Keine Marktquote:** 7000 US-Titel gegen ~50 DE-Titel in einem globalen Topf — EU verliert selbst ohne Ties fast immer. Fix: Quote je Markt (z. B. fix 120 US / 30 EU, oder EU mindestens `min(30, alle EU-Kandidaten)`); innerhalb der Quote nach (feinem) Score. Das ist kein „Verwässern": Die Alert-Budgets (5/Liste/Tag) gelten ohnehin getrennt, und ein EU-Kandidat mit Score 65 konkurriert live nie mit einem US-Titel um denselben Alert-Slot — die globale Kappung erzwingt eine Konkurrenz, die es im Rest des Systems gar nicht gibt.

**Aufwand: S–M · Nutzen: hoch** (stellt die EU-Schiene wieder her und macht den US-Teil der Liste erstmals qualitätssortiert).

### 5.2 121/150 spekulativ: plausibel, aber schief zum Alert-Budget
Die Dominanz ist erklärbar (`night_scan.py:14-17`: ADR ≥ 3 % ⇒ spekulativ; der Momentum-Vorfilter — nahe 20-Tage-Hoch, Volumenaufbau, RS — selektiert naturgemäß volatile Titel). Kein Datenfehler. Aber: Beide Listen haben dasselbe Live-Alert-Budget (5/Tag, `config.py:26`), die konservative Liste speist sich aus nur 29 Plätzen — ihr Budget wird selten ausgeschöpft, während spekulative 65er-Masse Plätze belegt. Wenn 5.1 mit Quoten gelöst wird, bietet sich zusätzlich eine **Listen-Quote** an (z. B. mind. 40 konservative Plätze), damit beide Erfolgsstatistiken (Spec §7, getrennte Auswertung!) genug Fälle sammeln.
**Aufwand: S (zusammen mit 5.1) · Nutzen: mittel.**

### 5.3 DE-Universum: 51 Titel statt ~160 laut Spec
**Code:** `config/universe_de.csv` (51 Zeilen), Spec §5: „DAX+MDAX+SDAX+TecDAX (~160 Titel)".

Die EU-Kandidatenbasis ist auf knapp ein Drittel des Designs verengt — verschärft 5.1 zusätzlich. Der Plan-Backlog (Z. 2158) kennt den Punkt; nach dem Quoten-Fix aus 5.1 wird er relevant, vorher nicht.
**Aufwand: S (CSV pflegen) · Nutzen: mittel.**

### 5.4 Score-Gewichte unkalibriert — die Verteilung zeigt, wo es klemmt
137× Score 65 vs. nur 8× Score 90 heißt konkret: Das Kriterium `volumen_aufbau` (25 P, `night_scan.py:26-27`) ist der eigentliche Selektor — fast alle anderen Kandidaten erfüllen „nahe_ausbruch + trend + RS" gleichzeitig (Korrelation der drei Kriterien untereinander ist hoch, sie messen verwandte Dinge). Die per Spec §6.1/§13 vorgesehene Backtest-Kalibrierung der Gewichte steht aus und setzt 1.4 (Backtest = Live-Regeln) voraus. Bis dahin liefert der Score wenig Rangordnungs-Information — ein Grund mehr für die kontinuierlichen Tiebreaker aus 5.1.
**Aufwand: M (nach 1.4) · Nutzen: mittel.**

---

## Was ausdrücklich gut ist (damit es beim Refactoring nicht verloren geht)

- **Dependency-Injection via `Deps`** (`live_observer.py:9-15`) — der Grund, warum der Trockenlauf (`scripts/run_dry_run.py`) und die Observer-Tests überhaupt möglich sind.
- **Atomare State-Writes** (`state.py:13-18`, tmp+`os.replace`) und der Rebase-Abort-Pfad in `commit_and_push` (`state.py:49-56`).
- **Alert-Historie selbstbeschneidend** (`live_observer.py:43`, nur gestern+heute) — kein State-Wachstum an dieser Stelle.
- **Disjunkte Telegram-Polling-Fenster** über `should_poll_commands` (`calendar_utils.py:27-30`) — elegant gelöst.
- **KI strikt degradierend** (`ai_review.py:22-23`): kann abwerten, nie blockieren — exakt Spec §6.3.
- **Kein Look-ahead im Backtest-Kern** und der Index-Alignment-Guard (`backtest.py:39-43`).
- **`recover_overnight`** (`live_observer.py:22-37`) — der Gap-Risiko-Fall „Runner stirbt vor Schlussgong" ist bedacht und getestet.

## Empfohlene Reihenfolge

1. **Sofort (alles S, zusammen < 1 Tag):** 1.2 (Heute-Bars), 1.7 (Missed-Budget), 2.4 (Blindflug-Warnung), 4.1 (`period="6mo"`), 2.1 (Kalender-Guard + Halbtage), 3.8 (split_batch).
2. **Diese Woche:** 1.1 (Volumenprofil), 5.1/5.2 (Quoten + Tiebreaker — ändert die Watchlist ab dem nächsten Nacht-Scan), 1.9 (Risikonormierung), 2.5 (Logging).
3. **Vor der 4–8-Wochen-Auswertung (Spec §7):** 1.4 (Backtest angleichen), 3.1 (Tests für run_session/build_deps/poll_commands), 1.5 (Survivorship dokumentieren), 5.4 (Gewichte kalibrieren).
4. **Backlog:** Rest der S/gering-Findings, 4.3 (adaptive Priorisierung), 5.3 (DE-Universum ausbauen — erst nach 5.1 sinnvoll).

*Hinweis: Alle Zahlen zur Watchlist stammen aus `state/watchlist.json`, Stand 08.07.2026 09:41; die Alphabetik der 65er-Einträge wurde programmatisch verifiziert (137/137 in sortierter Reihenfolge, Ende bei „O").*
