# Akademische Evidenz zur TrainSpotter-Strategie

**Datum:** 2026-07-08
**Autor:** Research-Analyst (Claude)
**Zweck:** Unabhängige Prüfung der wissenschaftlichen Evidenzlage zur Momentum-/Breakout-Strategie von TrainSpotter (siehe `docs/superpowers/specs/2026-07-07-trainspotter-design.md`). Jede Kernaussage ist mit Quelle belegt. Klar gekennzeichnet ist, wo die Evidenz **FÜR** und wo **GEGEN** unsere konkrete Umsetzung spricht.

> **Kernwarnung vorab:** Die akademische Momentum-Literatur belegt Effekte über **Formationsperioden von 3–12 Monaten und Haltedauern von Wochen bis Monaten**. TrainSpotters Haltedauer beträgt **1–3 Tage (spekulativ sogar nur Stunden, kein Overnight)**. In genau diesem Fenster (1 Tag – 1 Woche) dokumentiert die Literatur überwiegend das **Gegenteil von Momentum, nämlich Short-Term Reversal**. TrainSpotter fällt damit **nicht** in das durch die klassische Momentum-Literatur abgesicherte Zeitfenster. Details in Abschnitt 2 — das ist die wichtigste Erkenntnis dieses Berichts.

---

## 1. Kern-Evidenz: Ist Momentum überhaupt real?

**Ja — als Phänomen über mittlere Horizonte ist Momentum eine der robustesten empirischen Regelmäßigkeiten der Finanzwissenschaft.** Aber die belegten Horizonte sind Monate, nicht Tage.

### 1.1 Jegadeesh & Titman (1993) — Cross-Sectional Momentum (das Gründungspapier)
- **Quelle:** Jegadeesh, N. & Titman, S. (1993): "Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency", *The Journal of Finance* 48(1), 65–91. https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1993.tb04702.x (PDF: https://www.bauer.uh.edu/rsusmel/phd/jegadeesh-titman93.pdf)
- **Kernbefund:** Aktien, die über die **letzten 3–12 Monate** gestiegen sind (Winner), schlagen über die **folgenden 3–12 Monate** die Verlierer. Die beste Kombination (12M Formation / 3M Haltedauer) lieferte ~1,31 % pro Monat für das Winner-minus-Loser-Portfolio; die meistzitierte 6M/6M-Variante rund 1 % pro Monat. Nicht durch systematisches Risiko erklärbar.
- **Bezug zu uns:** Belegt die *Grundthese* („fahrende Züge fahren weiter"), **aber ausdrücklich für Formation und Haltedauer in Monaten**. Die Autoren fanden zudem, dass die Profite nach ~12 Monaten teilweise wieder zurückgehen (Reversal).

### 1.2 George & Hwang (2004) — 52-Wochen-Hoch-Momentum (unser nächster Verwandter)
- **Quelle:** George, T. J. & Hwang, C.-Y. (2004): "The 52-Week High and Momentum Investing", *The Journal of Finance* 59(5), 2145–2176. https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2004.00695.x
- **Kernbefund:** Die **Nähe zum 52-Wochen-Hoch** ist ein *besserer* Prädiktor künftiger Renditen als die vergangene Rendite selbst. Long die 30 % nächst am 52W-Hoch / Short die 30 % am weitesten entfernt: ~0,45 %/Monat roh, ~0,85 %/Monat risikoadjustiert. Verhaltensökonomische Erklärung: **Anchoring** — Anleger zögern, den Kurs über das „Ankerniveau" 52W-Hoch hinaus zu bieten; die Unterreaktion löst sich verzögert auf. Wichtig: Diese Gewinne **kehren sich langfristig NICHT um** (im Gegensatz zum klassischen Momentum).
- **Bezug zu uns:** **Stärkste theoretische Stütze** für TrainSpotters Kernkriterien „Kurs < 5 % unter 20-Tage-/52-Wochen-Hoch" und „Ausbruch über das Hoch". Der Anchoring-Mechanismus ist genau die Logik eines Breakouts über Widerstand. **ABER:** Auch hier ist die Haltedauer im Test **6 Monate**, nicht 1–3 Tage. Die Nähe zum Hoch ist ein *Ranking-Signal für Monatsrenditen*, keine Rechtfertigung für Tages-Trades.

### 1.3 Moskowitz, Ooi & Pedersen (2012) — Time-Series Momentum (Trend)
- **Quelle:** Moskowitz, T. J., Ooi, Y. H. & Pedersen, L. H. (2012): "Time Series Momentum", *Journal of Financial Economics* 104(2), 228–250. https://www.sciencedirect.com/science/article/abs/pii/S0304405X11002613 (PDF: https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf)
- **Kernbefund:** Über 58 liquide Futures (Aktienindizes, Währungen, Rohstoffe, Anleihen) sagt die **12-Monats-Überschussrendite** die künftige Rendite positiv voraus; der Trend hält **~12 Monate** an und kehrt sich danach teilweise um. Konsistent mit „Underreaction, dann Delayed Overreaction". Diversifiziert liefert die Strategie hohe risikoadjustierte Renditen, besonders in Extremmärkten.
- **Bezug zu uns:** Belegt Trend-Persistenz *absolut* (nicht nur relativ), was unsere „nur nach Norden fahrende Züge"-Filter (Kurs > SMA20 > SMA50, beide steigend) stützt. **Aber wieder: Formations- und Haltehorizont in Monaten.** Für Tagesgeschäft nicht einschlägig.

### 1.4 Meta-Evidenz: Momentum ist kein Zufallsfund
- **Quelle:** Asness, C., Frazzini, A., Israel, R. & Moskowitz, T. (2014): "Fact, Fiction and Momentum Investing", *Journal of Portfolio Management* 40(5). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2435323
- **Kernbefund:** Momentum-Prämie in **212 Jahren US-Daten (1801–2012)**, in UK-Daten seit der Viktorianischen Zeit, in 40 Ländern und über einem Dutzend Anlageklassen belegt; >20 Jahre Out-of-Sample seit Erstentdeckung. Widerlegt 10 gängige Mythen (u. a. „Momentum funktioniert nur short", „nur bei kleinen illiquiden Titeln").
- **Bezug zu uns:** FÜR die Grundthese. Aber das Papier bezieht sich durchgehend auf das **12-1-Monats-Standardmomentum**, nicht auf Tages-Trading.

**Zwischenfazit Abschnitt 1:** Die Momentum-*Familie* ist wissenschaftlich exzellent abgesichert. TrainSpotters *Signale* (Nähe zum Hoch, Aufwärtstrend, relative Stärke) sind gut motiviert. Die belegte Zeitachse ist jedoch durchgängig **Monate**. Das ist der Bruch, dem sich Abschnitt 2 widmet.

---

## 2. DIE ENTSCHEIDENDE FRAGE: Ist unsere Haltedauer von 1–3 Tagen durch die Literatur gedeckt? — Schonungslos ehrlich: NEIN.

**Kurzantwort:** Unser Kern-Zeithorizont (Einstieg heute, Ausstieg in 0–3 Tagen) liegt **genau im Bereich, in dem die Literatur überwiegend SHORT-TERM REVERSAL (Mean Reversion) dokumentiert — also das Gegenteil von Momentum.** Die klassische Momentum-Evidenz aus Abschnitt 1 deckt uns **nicht**; sie beginnt frühestens bei mehrmonatiger Formation. Wer TrainSpotter mit „Momentum ist doch belegt" rechtfertigt, verwechselt zwei verschiedene, teils gegenläufige Phänomene auf verschiedenen Zeitskalen.

### 2.1 Die belastende Evidenz (GEGEN uns)
- **Jegadeesh (1990):** "Evidence of Predictable Behavior of Security Returns", *Journal of Finance* 45(3). Aktien zeigen **Reversal über 1-Wochen- und 1-Monats-Intervalle**: Kauf der Vormonats-Verlierer / Verkauf der Vormonats-Gewinner verdient ~2 % pro Monat. D. h. auf **Monatssicht kehren kurzfristige Bewegungen um**. Referenz/Zusammenfassung: https://alphaarchitect.com/quantitative-momentum-research-short-term-return-reversal/
- **Lehmann (1990):** "Fads, Martingales, and Market Efficiency", *Quarterly Journal of Economics* 105(1). **Wochen-Reversal:** Vorwochen-Gewinner erzielen in der Folgewoche im Schnitt −0,35 % bis −0,55 %, Vorwochen-Verlierer +0,86 % bis +1,24 %. Contrarian-Strategie ~1,7 %/Woche (1962–1986). https://www.researchgate.net/publication/24091219_Fads_Martingales_and_Market_Efficiency
- **Konsequenz:** Genau auf der Tages-/Wochen-Skala, auf der TrainSpotter handelt, ist der **statistisch dominante Effekt Umkehr, nicht Fortsetzung**. Ein naives „Kaufe, was in den letzten Tagen am stärksten stieg, halte 1–3 Tage" arbeitet im Durchschnitt GEGEN diesen dokumentierten Effekt.

### 2.2 Die entlastende Evidenz (Gründe, warum unser Ansatz TROTZDEM verteidigbar sein kann)
TrainSpotter ist **kein** naiver „gestern-am-stärksten-gestiegen"-Kauf. Drei Literaturstränge liefern einen echten, aber schmalen Ausweg:

1. **Frog-in-the-Pan / Katalysator-Diskretheit — Da, Gurun & Warachka (2014):** "Frog in the Pan: Continuous Information and Momentum", *Review of Financial Studies* 27(7), 2171–2218. https://academic.oup.com/rfs/article-abstract/27/7/2171/1578455 (PDF: https://www3.nd.edu/~zda/Frog.pdf). **Kernbefund:** Momentum aus *kontinuierlicher, gradueller* Information ist stark und **kehrt langfristig nicht um** (5,94 % vs. −2,07 % je nach Informationsstruktur). — Ambivalent für uns: TrainSpotters volumengetriebene Ausbrüche sind oft *diskrete* News-Events (Gapper), was laut FIP eher zur *Rückkehr* neigt. Der Filter „Volumenaufbau über mehrere Tage" (§6.1) selektiert dagegen eher *graduelle* Aufmerksamkeit — das ist FIP-konform und positiv.
2. **Weekly-Continuation nach dem Reversal — Gutierrez & Kelley (2008):** "The Long-Lasting Momentum in Weekly Returns", *Journal of Finance* 63(1). **Kernbefund:** Auf den bekannten *kurzen* Wochen-Reversal folgt eine **lang anhaltende Fortsetzung**. D. h. der Reversal ist ein *sehr kurzes* Anfangsfenster; danach dominiert wieder Continuation. — Das relativiert Lehmann: ein Teil der 1-Wochen-Bewegung ist Liquiditäts-Reversal, der Rest echtes Momentum.
3. **52-Wochen-Hoch-Anchoring (George & Hwang, s. o.):** Ein *Ausbruch über ein etabliertes Hoch* ist qualitativ etwas anderes als „ist zuletzt schnell gestiegen". Der Anchoring-Mechanismus liefert genau am Ausbruchspunkt eine Unterreaktions-These. Aber: getestet auf Monatssicht.

### 2.3 Ehrliches Gesamturteil zu Frage 2
- Die **akademische Peer-Review-Evidenz für profitables Trading auf 1–3-Tages-Sicht ist dünn bis negativ.** Was TrainSpotter tut, gehört wissenschaftlich in die Kategorie **Intraday-/Swing-Breakout-Trading**, das primär in der **Praktiker-Literatur** (Abschnitt 4) und nicht in Top-Journals belegt ist.
- Die Strategie ist **nicht durch die zitierte Momentum-Literatur gedeckt**; sie *borgt* deren Signale (relative Stärke, Nähe zum Hoch, Trend) und *hofft*, dass die auf Monatssicht belegte Unterreaktion sich in ihrem gewählten Kurzfenster **schon manifestiert, bevor der Short-Term-Reversal-Effekt greift.** Ob das netto positiv ist, ist eine **empirisch offene Frage, die nur der eigene Backtest/Paper-Trade beantworten kann** — die Spec sieht das mit dem Live-Test (§9) richtig vor.
- **Das ist ehrlicherweise die Existenzfrage des Projekts.** Der Erfolg hängt weniger an „Momentum ist belegt" (das ist auf unserer Zeitskala unsicher) als an **exakter Ausführung, Volumenfilter-Qualität, Kostenkontrolle und disziplinierten Stops**. Die Realismus-Vereinbarung der Spec (40–55 % Trefferquote, „klein verlieren, groß gewinnen") ist damit die *korrekte* Rahmung — der Vorteil muss aus dem Auszahlungsprofil kommen, nicht aus einer sicheren Richtungswette.

---

## 3. Volumen als Momentum-Verstärker (FÜR uns — mit einer Warnung)

- **Quelle:** Lee, C. M. C. & Swaminathan, B. (2000): "Price Momentum and Trading Volume", *The Journal of Finance* 55(5), 2017–2069. https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00280 (PDF: https://www.lsvasset.com/pdf/research-papers/Price-Momentum-Trad-Vol-2000.pdf)
- **Kernbefund:** Vergangenes Handelsvolumen sagt **Stärke UND Persistenz** von Preismomentum voraus. Aber differenziert: **High-Volume-Winner kehren sich SCHNELLER um** über lange Horizonte (3–5 Jahre); Volumen ist ein Indikator für den „Momentum-Lebenszyklus".
- **Bezug zu uns — zweischneidig:**
  - **FÜR:** Bestätigt, dass ein Volumenfilter (unser ≥1,5× im Aufbau, ≥2× beim Ausbruch) informationstragend ist — Ausbrüche ohne Volumen zu ignorieren („Geisterzug") ist evidenzgestützt richtig.
  - **GEGEN/Vorsicht:** Lees Befund bezieht sich auf *hohes durchschnittliches Turnover* als Zeichen späten Zyklus / künftiger Umkehr. Sehr hohes Ausbruchsvolumen kann *Erschöpfung* (Blow-off) statt Fortsetzung anzeigen. Unser Kriterium ist ein *Volumen-Sprung relativ zum eigenen Schnitt* (kurzfristiger Impuls), nicht Lees *Niveau-Turnover* — die Befunde sind also nicht identisch, aber die Warnung „extremes Volumen ≠ garantierte Fortsetzung" bleibt.

---

## 4. Praktiker-Methoden: Track-Record vs. Marketing

Hier liegt TrainSpotters *tatsächliche* intellektuelle Heimat. Wichtig: Diese Methoden sind **nicht peer-reviewed**; ihre Belege sind Wettbewerbsresultate, Bücher und Backtests Dritter — anfällig für Survivorship- und Selektionsbias.

| Methode | Was dokumentiert ist | Was Marketing/unbelegt ist |
|---|---|---|
| **O'Neil CANSLIM** | AAII-Screen: Ø **24,4 %/Jahr** (bis Feb 2026), Platz 3 aller AAII-Screens (https://www.aaii.com/stockideas/article/10668-oneils-can-slim-revised-3rd-edition-approach). Akad. Näherung „OPBM II" (2013): +0,94 %/Monat vs. NASDAQ-100 (1999–2013). | CANSLIM-Fonds **CANGX** verlor real Geld (−20,5 % in 2008); Live-Fonds ≠ Backtest. CANSLIM ist zudem **Wochen–Monate**-Growth-Investing, nicht 1–3 Tage. |
| **Minervini SEPA/VCP** | Zwei US-Investing-Championship-Siege; auditierte **>334 % in 2021**. Klare Regeln (8-Punkte-Trend-Template, Volatilitäts-Kontraktion + Volumen-Breakout). https://www.finermarketpoints.com/post/what-is-a-vcp-pattern-mark-minervini-s-volatility-contraction-pattern-explained | Einzelperson, ein Wettbewerb, kein unabhängiger Langzeit-Track-Record; „consistently outperform" ist Anekdote. |
| **Qullamaggie (Kullamägi)** | Öffentlich dokumentierte Broker-Statements, berichtete **>100 Mio. $**. Methode = unsere fast 1:1: Top-Gainer der letzten 1–3 Monate → enge Konsolidierung an steigenden MAs → Ausbruch **auf Volumen** → Stop am Tagestief, Teilverkäufe, Trailing. https://www.timothysykes.com/blog/qullamaggie/ | Einzelperson in einem historischen Bullenmarkt (2017–2021); nicht repliziert, starker Überlebens-/Zeitraumbias. |
| **Turtle Trading (Dennis/Eckhardt)** | Original: ~80 %/Jahr, >150 Mio. $ in ~4 Jahren; mechanische **Donchian-Breakouts (20/55 Tage)** + ATR-Stops + Positionssizing. | Nach Veröffentlichung **fiel die Performance deutlich** — klassisches Alpha-Decay. Turtles handelten **Futures/Trends über Wochen–Monate**, nicht Aktien-Tagestrades. |

- **Fazit Abschnitt 4:** TrainSpotter kopiert im Kern die **Qullamaggie/Minervini-Schule** — plausible, in sich konsistente Regelwerke mit *beeindruckenden Einzel-Track-Records, aber schwacher wissenschaftlicher Validität* (n=1, Bullenmarkt-Fenster). Das ist keine Schande — es ist ehrlich zu benennen: **wir setzen auf ein Praktiker-Muster, dessen breite statistische Überlegenheit unbewiesen ist.** Turtles zeigen zudem, dass **veröffentlichte Breakout-Regeln an Wirkung verlieren** — ein Argument für laufende Rekalibrierung (die Spec sieht das §9 vor).

---

## 5. Bekannte Fallen

### 5.1 Momentum-Crashes (GEGEN uns — teilweise adressiert)
- **Quelle:** Daniel, K. & Moskowitz, T. J. (2016): "Momentum Crashes", *Journal of Financial Economics* 122(2), 221–247. https://www.kentdaniel.net/papers/published/jfe_16.pdf
- **Kernbefund:** Momentum erleidet seltene, aber heftige und anhaltende Verlustserien in **„Panik-Zuständen"** — nach Markteinbrüchen, bei hoher Volatilität und während scharfer Markt-Rebounds. Teilweise vorhersagbar; eine **dynamische, volatilitätsskalierte** Momentum-Version verdoppelt Sharpe/Alpha.
- **Bezug zu uns:** Unser Filter „Referenzindex intraday nicht < −1,5 %" (§6.2.4) und der Markt-Rückenwind-Check greifen die Grundidee auf (kein Momentum-Kauf in Panik). **Positiv.** Verbesserbar: Momentum-Crashes treten v. a. beim **Rebound** auf, nicht nur im Absturz — ein reiner Intraday-Index-Filter fängt das Rebound-Risiko nur teilweise. Vola-Skalierung (Positionsgröße runter bei hoher VIX/Index-Vola) wäre die evidenzbasierte Ergänzung.

### 5.2 Transaktionskosten bei Small Caps (ERNSTE Warnung für die spekulative Liste)
- **Quellen:** Lesmond, Schill & Zhou (2004): "The Illusory Nature of Momentum Profits", *JFE* — **Handelskosten können Momentumprofite bei kleinen/illiquiden Titeln vollständig aufzehren.** Gegenposition: Korajczyk & Sadka (2004): "Are Momentum Profits Robust to Trading Costs?", *Journal of Finance* 59(3) (https://www.kellogg.northwestern.edu/faculty/korajczy/htm/Korajczyk%20Sadka.jf2004.pdf) — Break-even erst bei 2–5 Mrd. $ Fondsgröße. Frazzini, Israel & Moskowitz (2015): "Trading Costs of Asset Pricing Anomalies" (https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies) — reale Kosten *deutlich* geringer als in der Literatur behauptet, aber *durch geschicktes Trading-Design* (Optimierung, Patience).
- **Bezug zu uns — kritisch:** Die gute Nachricht (Frazzini et al.) gilt für **große, geduldige, Kosten-optimierende Institutionen in liquiden Titeln**. TrainSpotters **spekulative Liste** ist das Gegenteil: **volatile Small Caps, Gapper, News-Titel** — genau Lesmonds Zone, in der Spreads + Slippage den Vorteil fressen. Unser 0,2-%-Slippage-Malus (§7) ist für Large Caps plausibel, für **spekulative Small-Cap-Ausbrüche vermutlich zu optimistisch** (reale Spreads + Impact bei Ausbruch oft 0,5–2 %+). **Das ist die materiell gefährlichste stille Annahme des Systems.**

### 5.3 Overnight- vs. Intraday-Renditen (schwerster konzeptioneller Einwand)
- **Quellen:** Cooper, Cliff & Gulen (2008): "Return Differences between Trading and Non-Trading Hours: Like Night and Day", SSRN 1004081 (https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1004081) — **die gesamte US-Aktien-Risikoprämie wird praktisch ÜBER NACHT verdient; Intraday-Renditen sind im Schnitt nahe null oder negativ.** Lou, Polk & Skouras (2019): "A Tug of War: Overnight Versus Intraday Expected Returns", *JFE* (https://personal.lse.ac.uk/polk/research/TugOfWar.pdf) — **Momentum-Renditen entstehen überwiegend ÜBER NACHT** und kehren sich intraday teilweise um; Institutionen handeln tagsüber *gegen* die Momentum-Charakteristik.
- **Bezug zu uns — schwerwiegend:**
  - Unsere **spekulative Liste schließt zwangsweise zum Handelsende (nie Overnight)** — aus Gap-Risiko-Erwägung nachvollziehbar, **schneidet aber laut Lou/Polk/Skouras genau das Fenster ab, in dem Momentum-Renditen tatsächlich anfallen.** Wir handeln bewusst nur die **intraday-Komponente**, die im Mittel schwächer/negativ ist. Das ist ein **fundamentaler Zielkonflikt**: Der Effekt, auf den wir setzen, wohnt statistisch in den Stunden, in denen wir per Regel *nicht investiert* sind.
  - Für die **konservative Liste** (Overnight bis 3 Tage erlaubt) ist das Bild günstiger — sie partizipiert an der Overnight-Prämie. **Evidenzbasierte Implikation:** Die konservative, Overnight-haltende Liste hat den *besseren* akademischen Rückenwind als die spekulative Intraday-Liste, obwohl letztere die „aufregendere" ist.

---

## 6. Parameter: Literatur/Praxis vs. unsere Wahl

| Parameter | Unsere Wahl (Spec) | Evidenz-/Praxis-Referenz | Urteil |
|---|---|---|---|
| Volumen beim Ausbruch | ≥ 2× (zeitanteilig) 20-Tage-Schnitt | Minervini/O'Neil-Praxis nennt oft **≥1,5×**, klassisch bis **≥2×**; Lee/Swaminathan bestätigt Volumen als Signal, warnt vor Extrem-Volumen | **Plausibel**, evtl. leicht streng. Extrem-Volumen (>4–5×) als *Warnflag* (Erschöpfung) ergänzen. |
| Volumenaufbau (Watchlist) | ≥ 1,5× 20-Tage-Schnitt (3–5 Tage) | Deckt sich mit Praktiker-Konsens | **Gut kalibriert.** |
| Abstand zum Hoch (Setup) | < 5 % unter 20-Tage-/52W-Hoch | George/Hwang: Nähe zum 52W-Hoch = Signal; Praktiker-VCP: Ausbruch aus enger Konsolidierung nahe Hoch | **Evidenzgestützt.** Empfehlung: enge Basis (VCP: Range-Kontraktion) explizit belohnen. |
| Relative Stärke | schlägt Index über 60 Tage (1–3 Monate) | Jegadeesh/Titman: 3–12M optimal; 60 Tage ist am *kurzen* Rand | **Grenzwertig kurz.** 3–6-Monats-RS zusätzlich prüfen — näher am belegten Optimum. |
| Stop-Weite | −3 % (kons.) / −6 % (spek.) unter Ausbruch | Turtle/Minervini nutzen **ATR-/Volatilitäts-basierte** Stops, keine festen % | **Verbesserungswürdig:** Fester %-Stop ignoriert Titelvolatilität; ATR-Vielfaches (z. B. 1,5–2× ADR) ist evidenznäher und passt zur ADR-Klassifizierung, die ihr ohnehin habt. |
| Ziel / Auszahlungsprofil | Ziel 1 +4 %/+10 %, Teilverkauf, Trailing | „Klein verlieren, groß laufen lassen" = Turtle-/Trendfolge-Kernprinzip; Daniel/Moskowitz stützt asymmetrisches Payoff | **Konzeptionell korrekt** — hier liegt der eigentliche Edge, nicht in der Richtungssicherheit. |
| Markt-Filter | Index intraday ≥ −1,5 % | Daniel/Moskowitz: kein Momentum in Panik/Hochvola | **Gut**, um Vola-Skalierung erweitern. |

---

## 7. Konkrete Regel-Änderungsvorschläge (priorisiert)

1. **Slippage-Malus für die spekulative Liste erhöhen** (§7): von 0,2 % auf **realistische 0,5–1,0 %** für Small-Cap-Gapper. Sonst überschätzt das Paper-Trading den Edge systematisch (Lesmond 2004). *Höchste Priorität — betrifft die Validitätsmessung selbst.*
2. **Stops auf ATR/ADR-Basis umstellen** statt fixer −3 %/−6 % (Turtle, Minervini). Ihr klassifiziert Titel bereits nach ADR — nutzt es: Stop = k × ADR unter Ausbruch (k≈1,5–2). Reduziert Ausstoppen bei volatilen Titeln und Übergröße bei ruhigen.
3. **Volatilitäts-/Crash-Filter ergänzen** (Daniel/Moskowitz 2016): Bei hoher Index-Vola oder frisch nach Markt-Rebound Positionsgröße reduzieren oder spekulative Alerts pausieren — nicht nur den −1,5-%-Intraday-Filter.
4. **Overnight-Konflikt transparent machen und messen** (Lou/Polk/Skouras 2019): Im Backtest **Overnight- vs. Intraday-Rendite je Liste getrennt ausweisen.** Erwartung: konservative (Overnight-)Liste schlägt spekulative (Intraday-)Liste pro Risikoeinheit. Falls ja, Ressourcen dorthin verlagern. Ggf. für ausgewählte spekulative High-Conviction-Trades ein kleines Overnight-Kontingent testen.
5. **Extrem-Volumen als Warnsignal**, nicht nur als Bestätigung (Lee/Swaminathan 2000): Ausbruchsvolumen > ~4–5× → KI-Bewertung soll „Blow-off/Erschöpfung?" explizit prüfen.
6. **Relative-Stärke-Fenster verlängern/ergänzen** auf 3–6 Monate zusätzlich zu 60 Tagen — näher am belegten 3–12M-Momentum-Optimum (Jegadeesh/Titman).
7. **Reversal-Risiko explizit im Backtest testen** (Jegadeesh 1990 / Lehmann 1990 / Gutierrez-Kelley 2008): Vergleicht Halte-Fenster 1 Tag vs. 3 Tage vs. 5 Tage vs. 2 Wochen. Wenn die 1–3-Tages-Fenster *schlechter* abschneiden als längere, ist das der Fingerabdruck des Short-Term-Reversal — dann Haltedauer verlängern.
8. **Erwartungsmanagement in Doku/Alerts:** Klar dokumentieren, dass die Strategie im wissenschaftlich *unsicheren* Kurzfrist-Fenster operiert und ihr Edge (falls vorhanden) aus **Ausführung + Payoff-Asymmetrie** stammt, nicht aus belegter Richtungsprognose.

---

## 8. Gesamtfazit

- **FÜR uns:** Die Momentum-/Breakout-*Signalfamilie* (Nähe zum Hoch, Aufwärtstrend, relative Stärke, Volumenbestätigung) ist wissenschaftlich exzellent belegt — auf **Monatssicht**. Der Volumenfilter, der Trendfilter, der Markt-Rückenwind-Check und das asymmetrische „klein verlieren, groß gewinnen"-Payoff sind evidenzkonform. George/Hwang (52W-Hoch-Anchoring) ist unsere stärkste theoretische Stütze.
- **GEGEN uns:** Unser **1–3-Tage-Horizont ist NICHT durch die zitierte Momentum-Literatur gedeckt** und kollidiert mit gut belegtem **Short-Term Reversal** (Jegadeesh 1990, Lehmann 1990). Der **Overnight-Anomalie-Befund** (Cooper/Cliff/Gulen 2008; Lou/Polk/Skouras 2019) sagt, dass gerade unsere zwangs-intraday spekulative Liste im *renditearmen* Fenster handelt. **Transaktionskosten** bei Small-Cap-Gappern (Lesmond 2004) sind das größte stille Risiko und im aktuellen Slippage-Modell unterschätzt.
- **Ehrliche Einordnung:** TrainSpotter ist wissenschaftlich ein **Praktiker-Breakout-System (Qullamaggie/Minervini-Schule)** mit anekdotischem, bullenmarkt-lastigem Track-Record — **nicht** eine Umsetzung der peer-reviewed Momentum-Prämie. Der in der Spec verankerte **Paper-Trading-Live-Test vor Echtgeld (§9)** ist deshalb nicht Kür, sondern **die einzige seriöse Methode, den ungewissen Kurzfrist-Edge zu beweisen oder zu widerlegen.** Genau richtig geplant.

---

## Quellenverzeichnis (kompakt)

1. Jegadeesh & Titman (1993), *J. Finance* 48(1) — Cross-Sectional Momentum 3–12M. https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1993.tb04702.x
2. George & Hwang (2004), *J. Finance* 59(5) — 52-Week-High-Momentum, Anchoring. https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2004.00695.x
3. Moskowitz, Ooi & Pedersen (2012), *JFE* 104(2) — Time-Series Momentum. https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
4. Asness, Frazzini, Israel & Moskowitz (2014), *J. Portf. Mgmt* 40(5) — Fact, Fiction & Momentum. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2435323
5. Jegadeesh (1990), *J. Finance* 45(3) — Short-Term (1-Monats-)Reversal. (Zusammenf.: https://alphaarchitect.com/quantitative-momentum-research-short-term-return-reversal/)
6. Lehmann (1990), *QJE* 105(1) — Weekly Reversal / Contrarian. https://www.researchgate.net/publication/24091219_Fads_Martingales_and_Market_Efficiency
7. Da, Gurun & Warachka (2014), *RFS* 27(7) — Frog in the Pan (kontinuierl. Info). https://www3.nd.edu/~zda/Frog.pdf
8. Gutierrez & Kelley (2008), *J. Finance* 63(1) — Long-Lasting Weekly Momentum.
9. Lee & Swaminathan (2000), *J. Finance* 55(5) — Price Momentum & Trading Volume. https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00280
10. Daniel & Moskowitz (2016), *JFE* 122(2) — Momentum Crashes. https://www.kentdaniel.net/papers/published/jfe_16.pdf
11. Lesmond, Schill & Zhou (2004), *JFE* — Illusory Nature of Momentum Profits (Small-Cap-Kosten).
12. Korajczyk & Sadka (2004), *J. Finance* 59(3) — Momentum Profits Robust to Costs? https://www.kellogg.northwestern.edu/faculty/korajczy/htm/Korajczyk%20Sadka.jf2004.pdf
13. Frazzini, Israel & Moskowitz (2015), AQR WP — Trading Costs of Asset Pricing Anomalies. https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies
14. Cooper, Cliff & Gulen (2008), SSRN 1004081 — Overnight vs. Intraday (Risikoprämie über Nacht). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1004081
15. Lou, Polk & Skouras (2019), *JFE* — A Tug of War: Overnight vs. Intraday (Momentum = überwiegend Overnight). https://personal.lse.ac.uk/polk/research/TugOfWar.pdf
16. O'Neil CANSLIM — AAII-Screen-Performance. https://www.aaii.com/stockideas/article/10668-oneils-can-slim-revised-3rd-edition-approach
17. Minervini SEPA/VCP. https://www.finermarketpoints.com/post/what-is-a-vcp-pattern-mark-minervini-s-volatility-contraction-pattern-explained
18. Qullamaggie (Kullamägi) — Methode & Track-Record. https://www.timothysykes.com/blog/qullamaggie/

*Hinweis: Praktiker-Quellen (16–18) sind nicht peer-reviewed; Track-Records unterliegen Survivorship-/Zeitraumbias.*
