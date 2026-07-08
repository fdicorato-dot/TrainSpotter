# KI-Formen & Rechenmethoden für TrainSpotter — Evaluation

**Datum:** 2026-07-08 · **Autor:** Quant-Architekt (Claude Fable 5) · **Status:** Read-only-Analyse, nichts committet
**Grundlage:** Design-Doc `docs/superpowers/specs/2026-07-07-trainspotter-design.md` sowie Code-Review von `night_scan.py`, `triggers.py`, `backtest.py`, `config.py`, `indicators.py`, `live_observer.py`, `ai_review.py`

**Bewertungsmaßstab:** Nutzen ÷ Komplexität unter den harten Constraints des Projekts — 0 € Betrieb, Gratis-Daten (yfinance 15-min-verzögert, Finnhub-Echtzeit nur US, Intraday-Historie ~60 Tage), GitHub Actions, öffentliches Repo, KI nur via Claude-CLI (Abo-Token), V1-Prinzip „Regeln sind die Quelle der Wahrheit, keine Blackbox".

**Ausgangsbefund aus dem Code (wichtig für die Priorisierung):**
Die Score-Gewichte in `night_scan.py` sind hart codiert (25/25/20/20+10, `SCORE_MIN=60`) und laut Design-Doc §13 explizit „per Backtest zu kalibrieren" — das ist noch offen. Und `indicators.time_prorated_volume_ratio()` proratiert das erwartete Tagesvolumen **linear** über die Handelszeit; zusätzlich stammt das US-Tagesvolumen aus dem ~15 Min verzögerten Yahoo-Cache (`live_observer.build_deps`), während der Preis in Echtzeit von Finnhub kommt. Beides zusammen verzerrt die zentrale Trigger-Bedingung Nr. 2 systematisch — dazu §6.

---

## 1. Kalibrierung statt ML

### 1a. Walk-Forward-Optimierung der Score-Gewichte

- **Was bringt sie konkret:** Die aktuellen Gewichte (25/25/20/20) sind Setzungen, keine Messungen. `backtest.py` simuliert bereits den Nacht-Scan Tag für Tag über Jahre — genau die Infrastruktur, die Walk-Forward braucht. Ablauf: Gewichte auf einem groben Raster (z. B. je Kriterium ∈ {0, 10, 20, 25, 30}) auf 2 Jahren „trainieren" (Profit-Faktor maximieren), auf den folgenden 6 Monaten out-of-sample messen, Fenster rollen. Nur die Out-of-Sample-Zahlen zählen. Nebeneffekt: Man sieht, ob die Gewichte über die Fenster **stabil** sind — instabile Gewichte sind selbst ein Warnsignal (Muster nicht robust).
- **Datenbedarf:** Tagesdaten 3–5 Jahre — mit yfinance vorhanden. ✔
- **Komplexität/Wartbarkeit:** Niedrig-mittel. Ein Skript um den bestehenden `simulate()`-Loop, reines pandas, keine neue Abhängigkeit. Läuft einmalig lokal oder als manueller Actions-Job, nicht im Live-Pfad.
- **Überanpassungsrisiko:** Mittel, aber durch Design beherrschbar: grobes Raster (kein Feintuning), wenige Parameter (4 Gewichte + `SCORE_MIN`), strikt Out-of-Sample berichten, 2022 muss im Test-Fenster vorkommen.
- **0€-Verträglichkeit:** Voll. Rechenzeit auf Actions/lokal, keine API-Kosten.
- **Empfehlung: V2.** Das Design-Doc verlangt diese Kalibrierung ohnehin (§6.1, §13); Walk-Forward ist die einzig ehrliche Form davon. Das ist kein ML, sondern das Validierungsprotokoll, das jede Regeländerung sowieso durchlaufen soll (§9).

### 1b. Bayessche Parameter-Schätzung

- **Was bringt sie konkret:** Posteriors statt Punktschätzungen für die Gewichte. Theoretisch eleganter, praktisch fast derselbe Output wie 1a — bei einem 5-Kriterien-Punkteschema mit grobem Raster liefert die Posterior-Verteilung keine handlungsrelevant andere Entscheidung.
- **Datenbedarf:** wie 1a. ✔
- **Komplexität/Wartbarkeit:** Hoch für vollen Ansatz (PyMC/Stan: schwere Abhängigkeit, lange Läufe, Wartungslast, für Außenstehende im öffentlichen Repo schwer nachvollziehbar).
- **Überanpassungsrisiko:** Niedrig (Priors regularisieren), aber das löst kein Problem, das 1a nicht auch löst.
- **0€-Verträglichkeit:** Technisch ja, aber Actions-Laufzeit und Abhängigkeitspflege stehen in keinem Verhältnis.
- **Empfehlung: VERWERFEN.** Nutzen gegenüber 1a marginal, Komplexität deutlich höher. **Miniatur-Ausnahme (kostenlos, 5 Zeilen scipy):** Beta-Binomial-Konfidenzintervall auf die Trefferquote in `/stats` — „46 % Trefferquote (90 %-Intervall: 35–57 %, n=42)". Das ist der einzige bayessche Baustein, der sich lohnt, und er verhindert, dass nach 4 Wochen aus 20 Trades falsche Sicherheit gezogen wird.

### 1c. Logistische Regression auf den 5 Kriterien

- **Was bringt sie konkret:** Ersetzt das Punkteschema durch datengeschätzte Gewichte — mathematisch die saubere Version von 1a: Koeffizienten × Kriterien = Score, voll interpretierbar, im Alert weiterhin als „Regel-Treffer mit Zahlen" darstellbar. Trainiert auf Backtest-Labels (Trade nach Ausbruch profitabel ja/nein), Tausende Fälle vorhanden. Zusatznutzen: Man erfährt, ob z. B. `volumen_aufbau` real prädiktiv ist oder nur Lärm — genau die Frage, für die das Paper-Trading-Buch die `reasons` je Trade mitschreibt (§7).
- **Datenbedarf:** Backtest-Trades (Tausende) aus Tagesdaten. ✔ Live-/Paper-Labels kommen später dazu.
- **Komplexität/Wartbarkeit:** Niedrig. 5–6 Features, L2-Regularisierung, sklearn (eine leichte, überall verfügbare Abhängigkeit) — oder bei striktem Dependency-Minimalismus 30 Zeilen Numpy-Gradientenabstieg. Nicht im Live-Pfad; das Modell exportiert nur 6 Zahlen nach `config.py`.
- **Überanpassungsrisiko:** Niedrig — 5 Features gegen Tausende Beobachtungen ist das Gegenteil der Blackbox-Sorge aus V1. Wichtig: **innerhalb** des Walk-Forward-Rahmens aus 1a evaluieren, nicht daneben.
- **0€-Verträglichkeit:** Voll.
- **Empfehlung: V2 — als die Kalibrierungsmethode innerhalb von 1a.** 1a liefert das Protokoll (Walk-Forward), 1c den Schätzer. Nicht beides getrennt bauen: die Grid-Suche aus 1a ist der Fallback, falls man sklearn vermeiden will; sonst direkt Logit. Das V1-Verbot („kein ML") zielte auf Blackbox + Überanpassung — eine regularisierte Logit auf 5 handverlesenen Kriterien verletzt beides nicht und bleibt zu 100 % erklärbar.

---

## 2. Regime-Erkennung

Motivation ist korrekt: Momentum-Crashes (Daniel/Moskowitz 2016) passieren typischerweise in Panik-Erholungen — hohe Volatilität, Markt unter langfristigem Trend, dann scharfer Rebound, bei dem die bisherigen Gewinner (= genau unsere Watchlist) underperformen. Der bestehende Filter (`INDEX_FILTER_PCT = -1.5` intraday) ist nur eine Tagesbremse ohne Regime-Gedächtnis: Am Tag **nach** dem −5 %-Crash steht der Index intraday bei +2 % und der Filter ist blind — das ist exakt das gefährliche Fenster.

### 2a. Hidden-Markov-Modell

- **Was bringt es konkret:** 2–3 latente Zustände auf Index-Renditen. In der Praxis: instabile Zustandszuordnung (Label-Switching), Neutrainings-Drift, `hmmlearn`-Abhängigkeit, und niemand kann im Alert erklären, warum „Zustand 2" heute gilt.
- **Datenbedarf:** ✔ (Index-Tagesdaten), aber irrelevant.
- **Komplexität/Wartbarkeit:** Hoch. **Überanpassungsrisiko:** Hoch (Regime-Grenzen sind freie Parameter).
- **Empfehlung: VERWERFEN.** Klassischer Fall von Methoden-Prestige ohne Mehrwert: Die 2b/2c-Regeln erfassen ≥ 90 % desselben Signals mit 0 % der Blackbox.

### 2b. VIX-Schwellen — **gratis verfügbar: ja**

`^VIX` ist über yfinance als Tagesdaten frei abrufbar (Index, kein Lizenzproblem beim Abruf); für EU analog `^V2TX`, notfalls realisierte 20-Tage-Vola des DAX als Ersatz (aus Daten, die ohnehin geladen werden).

### 2c. SMA200-Index-Filter

Der klassische Trendfilter (à la Faber): Referenzindex über/unter seiner 200-Tage-Linie.

- **Was bringt 2b+2c kombiniert konkret:** Ein 3-stufiges Regime als reine Regel, im Nacht-Scan berechnet und in `state/watchlist.json` mitgeschrieben:
  - **Risk-on** (Index > SMA200, VIX < ~25): Normalbetrieb.
  - **Vorsicht** (Index < SMA200 *oder* VIX 25–30): spekulative Liste halbiert (Alert-Budget 5→2), Warnhinweis im Alert.
  - **Risk-off** (Index < SMA200 *und* VIX > ~30): spekulative Alerts pausiert, konservative nur mit Warnung. Das adressiert genau das Momentum-Crash-Fenster: Panik-Erholungen finden praktisch immer unter der SMA200 bei erhöhtem VIX statt.
- **Datenbedarf:** ✔ vollständig gratis, ein zusätzlicher yfinance-Abruf pro Nacht.
- **Komplexität/Wartbarkeit:** Trivial — ~20 Zeilen, zwei Schwellen in `config.py`, im Backtest über 2020/2022 direkt validierbar (dieselben Tagesdaten!).
- **Überanpassungsrisiko:** Niedrig, solange die Schwellen kanonisch bleiben (200, 25/30) und nicht feinoptimiert werden.
- **0€-Verträglichkeit:** Voll.
- **Empfehlung: V2.** Antwort auf die Frage „welcher Filter schützt am einfachsten": **SMA200 + VIX-Schwelle als Regel — nicht HMM.** Vor Aktivierung im Backtest zeigen, dass der Filter 2022 den Profit-Faktor verbessert (sonst Schwellen unverändert lassen, nicht nachjustieren).

---

## 3. Gradient Boosting (XGBoost/LightGBM) zur Kandidaten-Rangfolge

- **Was bringt es konkret:** Theoretisch bessere Sortierung der ~150 Watchlist-Kandidaten (nicht Signal-Erzeugung — die Abgrenzung im Auftrag ist richtig). Praktisch: Bei 5–10 Features schlägt Boosting eine regularisierte Logit erst, wenn echte Nichtlinearitäten/Interaktionen vorliegen **und** genug saubere Labels da sind, um sie von Rauschen zu unterscheiden.
- **Realistisch mit ~150 Kandidaten/Tag und 0 Trade-Historie?** Nein. 150 Kandidaten/Tag sind *Inputs*, keine *Labels*. Trainieren ließe sich nur auf Backtest-Labels — dieselbe Quelle wie 1c, nur mit einem Modell, das jede Eigenheit der Tagesdaten-Simulation (pessimistische Stop-Reihenfolge, kein Intraday-Timing) mitlernt. Finanz-Labels haben ein brutales Rausch-zu-Signal-Verhältnis; Bäume finden darin zuverlässig Muster, die es nicht gibt.
- **Ab welcher Datenmenge sinnvoll?** Als Faustwert: frühestens ab **~500–1.000 realen (Paper-)Trades** mit stabilem Feature-Set und eingefrorener Regel-Basis — also nach 1–2 Jahren Betrieb, nicht nach 8 Wochen. Und selbst dann nur mit Tiefe ≤ 3, starker Regularisierung, Walk-Forward, und nur falls die Logit (1c) nachweislich an eine Decke stößt.
- **Komplexität/Wartbarkeit:** Mittel-hoch (Modell-Artefakte versionieren, Retraining-Kadenz, Feature-Drift). **Überanpassungsrisiko:** Hoch — der Hauptgrund, warum ML in V1 verworfen wurde, und der gilt hier unverändert. **0 €:** technisch ja.
- **Empfehlung: VERWERFEN** (für V2 *und* V3). Wiedervorlage nur unter drei kumulativen Bedingungen: >500 Paper-/Echt-Trades, Logit-Plateau belegt, Regeln seit ≥ 6 Monaten eingefroren. Bis dahin ist jede Stunde hier besser in §6 investiert.

---

## 4. LLM-Nutzung ausbauen

Ist-Zustand: `ai_review.py` ruft `claude -p` als Subprozess je Trigger (≤ ~10–20 Aufrufe/Tag bei Alert-Disziplin §6.5). Abo-Token, keine API-Kosten — aber Abo-Kontingente (5-h-Fenster) sind endlich und werden mit der interaktiven Nutzung geteilt.

### 4a. News-Sentiment je Kandidat im Nacht-Scan

- **Was bringt es konkret:** Kandidaten mit frischem Katalysator (Upgrade, Auftrag, FDA) höher sortieren, Kandidaten mit Negativ-News aussortieren — bevor der Live-Beobachter Ressourcen auf sie verwendet.
- **Kontingent-Kosten:** 150 einzelne CLI-Aufrufe/Nacht sind indiskutabel — jeder Subprozess-Start kostet 10–30 s (Nacht-Scan liefe Stunden) und das Kontingent würde spürbar belastet. Machbar ist nur **Batching**: 1–2 Aufrufe mit den Schlagzeilen der Top-30 bis Top-50, JSON-Array zurück. yfinance-/Finnhub-Headlines sind gratis vorhanden, aber nachts oft dünn/veraltet — der Informationsgewinn ist unsicher.
- **Komplexität:** Niedrig (Prompt + Parser existieren dem Muster nach schon). **Überanpassung:** n/a. **0 €:** ✔ bei Batching.
- **Empfehlung: V3, schlanke Batch-Variante (Top-30).** Erst nachweisen, dass die Regel-Pipeline stabil läuft; dann als reiner **Tie-Breaker der Sortierung** einführen (LLM darf umsortieren, nie qualifizieren — konsistent mit §6.3 „abwerten, nicht erfinden").

### 4b. Earnings-Kalender-Awareness

- **Was bringt es konkret:** Viel — ein Breakout am Tag vor den Zahlen ist eine Lotterie, kein Zug; und ein Gap nach Zahlen ist ein anderes Setup als ein technischer Ausbruch. Aber: **Dafür braucht es kein LLM.** Finnhubs Gratis-Tier hat einen Earnings-Kalender-Endpoint (`/calendar/earnings`); yfinance liefert Termine je Ticker als Fallback.
- **Umsetzung:** Nacht-Scan flaggt `earnings_in_days` je Kandidat; Regel: Earnings innerhalb ±1 Handelstag → konservative Liste raus, spekulative mit explizitem Warnhinweis im Alert („Zahlen morgen — Event-Risiko"). Eine Zeile im Alert-Format, eine Abfrage pro Nacht.
- **Komplexität:** Niedrig. **0 €:** ✔. **Überanpassung:** keine.
- **Empfehlung: V2 — als Regel, nicht als LLM-Feature.** Bestes Nutzen/Komplexitäts-Verhältnis im ganzen LLM-Block, gerade weil das LLM wegfällt.

### 4c. Tägliche „Warum lief gestern schief"-Retrospektive

- **Was bringt es konkret:** Genau in der 4–8-Wochen-Validierungsphase Gold wert: 1 CLI-Aufruf/Abend über die geschlossenen Trades des Tages (CSV liegt mit `reasons`, Scores, Exit-Gründen vor — §7 hat die Datenlage dafür bewusst geschaffen). Output in die Abend-Bilanz: „3 von 4 Stops waren Geisterzüge mit vol_ratio < 2,5 in der ersten Handelsstunde" — Muster, die ein Mensch erst nach Wochen sieht. Wichtig: Output ist **Beobachtung, nie automatische Regeländerung** (jede Änderung geht weiter durch den Backtest, §9).
- **Kontingent-Kosten:** ~1 Aufruf/Tag — vernachlässigbar.
- **Komplexität:** Niedrig (Muster von `ai_review.py` wiederverwenden, Anhang an `reports.py`-Abendbilanz).
- **Empfehlung: V2.**

---

## 5. Konfidenz & Sizing

### 5a. Conformal Prediction

- **Was bringt es konkret:** Verteilungsfreie Unsicherheitsbänder — konzipiert für Punktvorhersagen mit Kalibrierungs-Set. TrainSpotter macht aber keine Punktvorhersagen: Es klassifiziert binäre Trade-Ausgänge. Dafür kollabiert Conformal Prediction praktisch auf ein Binomial-Konfidenzintervall — das die Beta-Binomial-Miniatur aus 1b bereits liefert. Mit n < 100 Paper-Trades wären konforme Bänder ohnehin so breit, dass sie nur bestätigen, was das Wilson-Intervall schon sagt.
- **Komplexität:** Mittel (Kalibrierungs-Split-Logik, Austauschbarkeits-Annahme bei Zeitreihen fragwürdig). **0 €:** ✔, irrelevant.
- **Empfehlung: VERWERFEN.** Ehrliche Unsicherheit ja — aber via Wilson-/Beta-Intervall in `/stats` (siehe 1b), nicht via Conformal-Maschinerie.

### 5b. Kelly-Criterion / Fractional Kelly

- **Was bringt es konkret:** Positions-Sizing aus Trefferquote p und Gewinn/Verlust-Verhältnis b — die einzig prinzipienbasierte Antwort auf „wie viel pro Trade", sobald Echtgeld ansteht. Formel ist eine Zeile.
- **Aber:** Paper-Trading nutzt bewusst fixe 1.000 € (Vergleichbarkeit, §7) — Sizing hat dort nichts zu suchen. Und Kelly ist berüchtigt empfindlich gegen Schätzfehler: Nach 8 Wochen liegen vielleicht 100–150 Trades vor; die p-Unsicherheit (siehe 1b!) macht Voll-Kelly zum Ruin-Beschleuniger. Praxis: **Viertel-Kelly, gedeckelt** (z. B. max. 10 % des Kapitals), getrennt je Liste, p und b aus der Paper-Statistik mit dem Beta-Intervall-Unterrand statt dem Punktschätzer.
- **Komplexität:** Trivial. **0 €:** ✔.
- **Empfehlung: V3 — exakt zum Echtgeld-Übergang,** nicht früher. In V2 nur die Datengrundlage sichern (Statistik je Liste läuft bereits).

---

## 6. Mikrostruktur/Berechnung — **hier liegt der größte unmittelbare Hebel**

### 6a. U-förmige Intraday-Volumenkurve statt linearer Proration + korrektes RVOL

- **Der Befund im Code:** `time_prorated_volume_ratio()` rechnet `expected = avg_daily_volume × elapsed_frac` — linear. Reales US-Aktienvolumen ist stark U-förmig: In den ersten 30 Minuten laufen typischerweise ~12–18 % des Tagesvolumens (linear unterstellt: ~5 %), über Mittag fast nichts, zum Schluss wieder viel. Konsequenz: Das erwartete Volumen wird **morgens massiv unterschätzt → vol_ratio systematisch überhöht → die 2×-Schwelle ist in der ersten Stunde viel zu leicht zu reißen.** Genau morgens entstehen die meisten Breakouts — die wichtigste Filterbedingung des Systems (Trigger Nr. 2, „Geisterzug"-Schutz) ist also zur Hauptgeschäftszeit am schwächsten. Mittags kippt der Fehler in die Gegenrichtung (zu streng). **Verschärfung im US-Betrieb:** Das Tagesvolumen kommt aus dem ~15 Min verzögerten Yahoo-Cache (nur alle 5 Zyklen erneuert), der Preis in Echtzeit von Finnhub — das *gemessene* Volumen hinkt zusätzlich hinterher; beide Fehler überlagern sich zeitabhängig.
- **Fix:** RVOL korrekt = kumuliertes Volumen bis Uhrzeit t ÷ **durchschnittliches kumuliertes Volumen bis zur selben Uhrzeit**. Umsetzung mit Gratis-Daten: entweder (i) statische Bucket-Gewichtstabelle je Markt (30-Min-Buckets, die US-U-Kurve ist stabil und dokumentiert) in `config.py`, oder (ii) empirisch aus den ~60 Tagen yfinance-Intraday-Historie geschätzt und monatlich vom Nacht-Scan aktualisiert. Variante (i) reicht; (ii) ist ein Nice-to-have. Zusätzlich `elapsed_frac` beim US-Markt um den bekannten Volumen-Lag (~15 Min + Cache-Alter) korrigieren — zwei Zeilen.
- **Datenbedarf:** ✔ (statische Tabelle: gar keiner; empirisch: 60 Tage Intraday reichen für eine Kurvenform).
- **Komplexität:** Sehr niedrig — eine Funktion ersetzt eine Funktion, Unit-Tests nach §11-Muster. **Überanpassung:** keine (Korrektur eines bekannten systematischen Fehlers). **0 €:** ✔.
- **Empfehlung: V2, Priorität 1.** Kein anderes Item in diesem Report verbessert die Alert-Qualität so direkt und so billig. Sollte vor jeder Kalibrierung (§1) passieren, sonst kalibriert man auf einen verzerrten Trigger.

### 6b. VWAP als Einstiegs-/Trailing-Referenz

- **Was bringt es konkret:** „Nur einsteigen, wenn Kurs > VWAP" filtert überdehnte Einstiege; Trailing unter VWAP ist ein bewährter Intraday-Anker. Überschneidet sich aber mit vorhandenen Mechanismen: Die „Zug verpasst"-Grenze (+4 %/+6 %) begrenzt Überdehnung bereits, und das Trailing unter dem 30-Min-Tief (§7) existiert.
- **Datenbedarf:** Intraday-Bars nötig; yfinance liefert sie 15 Min verzögert — als Trailing-Referenz für wenige offene Positionen brauchbar, als Echtzeit-Einstiegsfilter im US-Handel grenzwertig (VWAP-Stand ist 15 Min alt, Preis ist live — inkonsistenter Vergleich).
- **Komplexität:** Mittel — die Live-Schleife ist Quote-basiert, nicht Bar-basiert; VWAP heißt zusätzliche Bar-Abrufe je Zyklus und ein zweiter Datenpfad. **Überanpassung:** niedrig. **0 €:** ✔, aber API-Budget-Druck.
- **Empfehlung: V3.** Solide Idee, aber der Grenznutzen gegenüber „Zug verpasst"-Grenze + 30-Min-Tief-Trailing rechtfertigt den zweiten Datenpfad in V2 nicht. Wiedervorlage, falls die Paper-Statistik „zu späte Einstiege" als Verlustmuster zeigt (das wird die Retrospektive 4c sichtbar machen).

---

## 7. Zusätzliche Kandidaten (Quant-Architekt)

Nur zwei, beide schlagen das Kalkül klar:

### 7a. ATR-/ADR-adaptive Stops statt fixer Prozent-Stops

- **Befund:** `STOP_PCT` ist fix (−3 %/−6 % unter Ausbruchsniveau) — aber die Watchlist mischt per Konstruktion Titel mit ADR 1,5 % und ADR 8 %+. Für einen 8 %-ADR-Titel ist ein 6 %-Stop **innerhalb der normalen Tagesschwankung** — er wird vom Rauschen gerissen, nicht vom Scheitern des Ausbruchs. Für einen 1,6 %-ADR-Titel ist −3 % unnötig weit.
- **Fix:** Stop = Ausbruchsniveau − k × ADR (z. B. k = 1,0 konservativ / 1,5 spekulativ), gedeckelt durch die bisherigen Maxima. ADR wird je Kandidat bereits berechnet und in der Watchlist gespeichert (`adr_pct`) — die Daten liegen buchstäblich schon im Dict.
- **Komplexität:** Sehr niedrig (eine Formel in `triggers.py` + `backtest.py`, per Backtest gegen fixe Stops validierbar). **Überanpassung:** niedrig (ein Parameter k je Liste, kanonische Werte). **0 €:** ✔.
- **Empfehlung: V2.**

### 7b. Bootstrap-/Sensitivitätsanalyse des Backtests

- **Was bringt es konkret:** Bevor irgendeine Kalibrierung (§1) geglaubt wird: (i) Block-Bootstrap über die Backtest-Trades → Konfidenzintervall für den Profit-Faktor („PF 1,4, 90 %-Intervall 1,1–1,7" ist eine andere Entscheidungsgrundlage als „PF 1,4"); (ii) Sensitivitäts-Sweep: jeden Parameter in `config.py` ±20 % variieren — bricht die Strategie, war sie nie robust. Das ist die direkte Antwort auf die Überanpassungs-Sorge, die ML in V1 verworfen hat — angewandt auf die eigenen Regeln.
- **Datenbedarf:** ✔ (nutzt nur vorhandene Backtest-Outputs). **Komplexität:** Niedrig (Numpy-Resampling + Schleife über Parameter). **0 €:** ✔.
- **Empfehlung: V2 — als Pflicht-Torwächter vor 1a/1c.** Ohne 7b ist jede Gewichts-Kalibrierung Zahlenkosmetik.

---

## Priorisierte Empfehlungsliste

### V2 (max. 5 Punkte, in dieser Reihenfolge)

| # | Maßnahme | Warum zuerst |
|---|---|---|
| 1 | **U-Kurven-RVOL** (6a) inkl. US-Volumen-Lag-Korrektur | Behebt einen aktiven systematischen Fehler in der wichtigsten Trigger-Bedingung; winzig im Aufwand; Voraussetzung für sinnvolle Kalibrierung |
| 2 | **Regime-Filter SMA200 + VIX als Regel** (2b+2c) | Schützt vor Momentum-Crash-Fenstern, die der intraday −1,5 %-Filter nicht sieht; ~20 Zeilen; im Backtest über 2022 validierbar |
| 3 | **Earnings-Kalender-Flag als Regel** (4b) | Event-Risiko raus aus konservativ, Warnung bei spekulativ; Finnhub-Gratis-Endpoint; kein LLM nötig |
| 4 | **Backtest-Torwächter: Bootstrap + Sensitivitäts-Sweep** (7b), dann **Walk-Forward-Kalibrierung via logistischer Regression** (1a+1c) + Beta-Intervalle in `/stats` (1b-Miniatur) | Erfüllt Design-Doc §13 ehrlich; interpretierbar; erst Robustheit prüfen, dann kalibrieren |
| 5 | **ATR-adaptive Stops** (7a) + **tägliche LLM-Retrospektive** (4c) | Stops passend zur Titel-Volatilität (Daten liegen vor); Retrospektive maximiert den Lernwert der Validierungsphase bei ~1 CLI-Aufruf/Tag |

### V3 (zurückgestellt, nicht verworfen)

- **Kelly-Sizing (Viertel-Kelly, gedeckelt)** — exakt zum Echtgeld-Übergang, mit Beta-Intervall-Unterrand statt Punktschätzer (5b)
- **VWAP-Referenz** — nur falls die Retrospektive „zu späte Einstiege" als Verlustmuster belegt (6b)
- **Nächtliches News-Sentiment als Batch für Top-30** — nur als Sortier-Tie-Breaker, nie als Qualifikator (4a)

### VERWORFEN — explizit und warum

- **Hidden-Markov-Regime-Modell (2a):** Blackbox mit instabilen Zuständen und Retraining-Drift; die SMA200+VIX-Regel liefert ≥ 90 % des Schutzes bei ~0 % der Komplexität und bleibt im Alert erklärbar.
- **XGBoost/LightGBM (3):** Mit 0 Trade-Historie nicht trainierbar außer auf Backtest-Labels, wo es Simulations-Artefakte mitlernt; bei 5–10 Features kein belegbarer Vorteil über die regularisierte Logit; höchstes Überanpassungsrisiko im gesamten Katalog — exakt der Grund, aus dem ML in V1 verworfen wurde. Wiedervorlage frühestens bei >500 realen Trades, belegtem Logit-Plateau und ≥ 6 Monate eingefrorenen Regeln.
- **Volle Bayessche Parameter-Schätzung (1b):** PyMC/Stan-Wartungslast ohne handlungsrelevanten Mehrwert gegenüber Walk-Forward + Logit; einzig die 5-Zeilen-Beta-Binomial-Intervalle für `/stats` überleben als Miniatur.
- **Conformal Prediction (5a):** Kollabiert bei binären Trade-Ausgängen praktisch auf ein Binomial-Intervall, das Wilson/Beta bereits liefern; Austauschbarkeits-Annahme bei Marktzeitreihen zweifelhaft; Maschinerie ohne Erkenntnisgewinn.
- **News-Sentiment je Kandidat als Einzel-Aufrufe (4a in der naiven Form):** 150 CLI-Subprozesse pro Nacht sind zeitlich (Stunden) und kontingentseitig indiskutabel; nur die Batch-Variante bleibt als V3-Kandidat.

---

**Leitprinzip dieses Reports:** Alles Empfohlene bleibt im V1-Geist — Regeln als Quelle der Wahrheit, jede Zahl im Alert erklärbar, jede Änderung erst durch den Backtest (§9). Kein einziger V2-Punkt führt eine Blackbox ein; vier von fünf sind reine Regel- oder Rechenkorrekturen, der fünfte ist eine interpretierbare 6-Koeffizienten-Kalibrierung unter Walk-Forward-Disziplin.

*Hinweis: Analyse, keine Anlageberatung.*
