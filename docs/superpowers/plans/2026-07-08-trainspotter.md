# TrainSpotter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Momentum-Scanner, der täglich eine Watchlist baut („Wer steht am Bahnsteig?"), während der Handelszeiten anfahrende Züge erkennt (Ausbruch + Volumen), Alerts per Telegram schickt und jeden Alert als virtuellen Paper-Trade bis zum Ausstieg verfolgt.

**Architecture:** Zweistufig: Nacht-Scan filtert ~7000 US + ~50 DE Titel auf ~150 Watchlist-Kandidaten (Bahnsteig-Score); ein Live-Beobachter (long-running GitHub-Actions-Job je Marktsitzung) prüft die Watchlist rollierend (US: Finnhub-Echtzeitpreise + Yahoo-Volumen; EU: Yahoo ~15 Min. verzögert) und löst Alerts aus. Zustand liegt als JSON/CSV im Repo (Job committet). KI-Bewertung pro Treffer via Claude Code CLI headless (`claude -p`) mit Abo-Token.

**Tech Stack:** Python 3.12, pandas, yfinance, requests, pytest; GitHub Actions (öffentliches Repo); Telegram Bot API; Finnhub Gratis-Tier; Claude Code CLI (`CLAUDE_CODE_OAUTH_TOKEN`).

**Spec:** `docs/superpowers/specs/2026-07-07-trainspotter-design.md` — alle Schwellwerte dort in §4–§6.

## Global Constraints

- Laufende Kosten: **0 €** (Gratis-Datenquellen, öffentliches Repo, KI über Abo-Token — nie API-Key-Abrechnung einbauen)
- **Kein Alert ohne Stop-Loss** — ausnahmslos
- Zwei Listen mit festen Parametern: konservativ (Stop −3 %, Ziel 1 +4 %, max. 3 Handelstage) / spekulativ (Stop −6 %, Ziel 1 +10 %, Zwangsschluss zum Handelsende)
- Paper-Trades immer mit 0,2 % Slippage-Malus und 1.000 € virtueller Positionsgröße
- Max. 5 Alerts pro Liste pro Tag, max. 1 Alert pro Ticker pro Tag (Alert-ID = `TICKER-YYYY-MM-DD`)
- Ein kranker Ticker darf nie einen Scan stoppen (try/except je Ticker, loggen, weiter)
- Alle Nutzer-Nachrichten (Telegram) auf **Deutsch**
- Datenschicht austauschbar halten: kein `yfinance`-Import außerhalb `trainspotter/data/`
- Tests laufen ohne Netz: `TRAINSPOTTER_NO_GIT=1` deaktiviert Git-Operationen, HTTP/Subprozesse werden gemockt
- Python ≥ 3.11 (zoneinfo), Zeitzonen immer explizit (`America/New_York`, `Europe/Berlin`, UTC)

## Dateistruktur (Ziel)

```
trainspotter/
  __init__.py  config.py  indicators.py  state.py  calendar_utils.py
  universe.py  night_scan.py  triggers.py  paper_trading.py
  telegram_bot.py  ai_review.py  reports.py  live_observer.py  backtest.py
  data/__init__.py  data/yahoo.py  data/finnhub.py
scripts/
  run_night_scan.py  send_depesche.py  send_bilanz.py  run_observer.py
  run_backtest.py  run_dry_run.py  send_test_message.py
config/universe_de.csv
state/            (zur Laufzeit: watchlist.json, positions_us.json, positions_eu.json,
                   alerts_sent.json, telegram_offset.json, history/trades_us.csv, trades_eu.csv)
tests/            (test_* je Modul, fixtures/)
.github/workflows/ tests.yml night-scan.yml depesche.yml observer-eu.yml observer-us.yml bilanz.yml
```

---

### Task 1: Projektgerüst & Konfiguration

**Files:**
- Create: `requirements.txt`, `pyproject.toml`, `.gitignore`, `trainspotter/__init__.py`, `trainspotter/config.py`, `tests/test_config.py`, `state/.gitkeep`, `state/history/.gitkeep`

**Interfaces:**
- Produces: `trainspotter.config` — alle Konstanten (Namen exakt wie unten), von allen Folgetasks als `import trainspotter.config as cfg` konsumiert.

- [ ] **Step 1: Dateien anlegen**

`requirements.txt`:
```
pandas>=2.0
yfinance>=0.2.40
requests>=2.31
pytest>=8.0
PyYAML>=6.0
```

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

`.gitignore`:
```
__pycache__/
*.pyc
.pytest_cache/
```

`trainspotter/__init__.py`: leer.

`trainspotter/config.py`:
```python
"""Alle Parameter des Systems. Quelle: Design-Doc §4-§6."""

# Universum-Vorfilter
MIN_PRICE = 2.0                 # $ bzw. EUR
MIN_DOLLAR_VOLUME = 5_000_000   # Ø Tagesumsatz

# Nacht-Scan (Bahnsteig-Score)
VOL_BUILDUP_RATIO = 1.5         # letzte 5 Tage vs. 20-Tage-Basis
RECENT_VOL_DAYS = 5
BASELINE_VOL_DAYS = 20
NEAR_BREAKOUT_PCT = 5.0         # max. Abstand unter Widerstand
MAX_ABOVE_BREAKOUT_PCT = 1.0    # schon weiter drüber -> abgefahren, raus
BREAKOUT_WINDOW = 20            # Tage für Widerstandsniveau (ohne heute)
RS_DAYS = 60                    # relative Stärke Zeitraum
SCORE_MIN = 60
WATCHLIST_SIZE = 150
ADR_MIN_KONS = 1.5              # Ø-Tagesspanne %
ADR_MIN_SPEC = 3.0

# Live-Trigger
TRIGGER_VOL_RATIO = 2.0         # zeitanteiliges Volumen
INDEX_FILTER_PCT = -1.5         # Index intraday darunter -> nur spek. + Warnung
MISSED_TRAIN_PCT = {"konservativ": 4.0, "spekulativ": 6.0}
STOP_PCT = {"konservativ": 3.0, "spekulativ": 6.0}      # unter Ausbruchsniveau
TARGET1_PCT = {"konservativ": 4.0, "spekulativ": 10.0}  # über Einstieg
MAX_ALERTS_PER_LIST = 5

# Paper-Trading
SLIPPAGE_PCT = 0.2
POSITION_SIZE_EUR = 1000.0
TRAIL_WINDOW_MIN = 30           # Trailing: Tief der letzten 30 Min
TRAIL_BUFFER_PCT = 0.5          # Stop knapp UNTER dem Tief
MAX_HOLD_DAYS_KONS = 3

# Betrieb
CYCLE_SECONDS = 120
US_VOLUME_REFRESH_CYCLES = 5    # Yahoo-Volumen-Cache alle N Zyklen
LISTEN = ("konservativ", "spekulativ")

# Indizes je Markt (Yahoo-Symbole)
INDEX_SYMBOL = {"us": "^GSPC", "eu": "^GDAXI"}

DISCLAIMER = "Hinweis: Analyse, keine Anlageberatung."
```

`tests/test_config.py`:
```python
import trainspotter.config as cfg

def test_listen_parameter_vollstaendig():
    for d in (cfg.MISSED_TRAIN_PCT, cfg.STOP_PCT, cfg.TARGET1_PCT):
        assert set(d) == set(cfg.LISTEN)

def test_kernwerte():
    assert cfg.STOP_PCT["konservativ"] == 3.0
    assert cfg.TARGET1_PCT["spekulativ"] == 10.0
    assert cfg.SLIPPAGE_PCT == 0.2
```

- [ ] **Step 2: Abhängigkeiten installieren und Test ausführen**

Run: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pytest tests/test_config.py -v`
Expected: 2 passed. (Alle weiteren `pytest`-Aufrufe: `.venv/bin/pytest`.)

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "chore: Projektgeruest und Konfiguration"
```

---

### Task 2: Indikatoren

**Files:**
- Create: `trainspotter/indicators.py`, `tests/test_indicators.py`

**Interfaces:**
- Produces: `sma(series, window) -> pd.Series`, `volume_buildup_ratio(volumes) -> float`, `adr_pct(high, low, close, window=20) -> float`, `relative_strength(stock_close, index_close, days) -> float`, `breakout_level(high, window=20) -> float` (**ohne den letzten Tag**), `time_prorated_volume_ratio(volume_today, avg_daily_volume, elapsed_frac) -> float`, `distance_pct(price, level) -> float`

- [ ] **Step 1: Failing Tests schreiben** — `tests/test_indicators.py`:

```python
import pandas as pd, pytest
from trainspotter import indicators as ind

def test_sma():
    assert ind.sma(pd.Series([1, 2, 3, 4, 5]), 5).iloc[-1] == 3.0

def test_volume_buildup_ratio():
    vols = pd.Series([100.0] * 20 + [200.0] * 5)   # Basis 100, letzte 5 Tage 200
    assert ind.volume_buildup_ratio(vols) == pytest.approx(2.0)

def test_volume_buildup_zu_wenig_daten():
    assert ind.volume_buildup_ratio(pd.Series([100.0] * 10)) == 0.0

def test_adr_pct():
    n = 20
    df = {"h": pd.Series([105.0] * n), "l": pd.Series([95.0] * n), "c": pd.Series([100.0] * n)}
    assert ind.adr_pct(df["h"], df["l"], df["c"]) == pytest.approx(10.0)

def test_relative_strength():
    stock = pd.Series([100, 102, 104, 106, 108, 110.0])   # +10 % ueber 5 Tage
    index = pd.Series([100, 101, 102, 103, 104, 105.0])   # +5 %
    assert ind.relative_strength(stock, index, days=5) == pytest.approx(5.0)

def test_breakout_level_ohne_heute():
    highs = pd.Series([10, 12, 11, 15, 14, 99.0])  # 99 ist "heute" -> zaehlt nicht
    assert ind.breakout_level(highs, window=5) == 15.0

def test_time_prorated_volume_ratio():
    # 600k bei 30 % Sitzung, Schnitt 1M/Tag -> erwartet 300k -> Ratio 2.0
    assert ind.time_prorated_volume_ratio(600_000, 1_000_000, 0.3) == pytest.approx(2.0)

def test_distance_pct():
    assert ind.distance_pct(95.0, 100.0) == pytest.approx(-5.0)
    assert ind.distance_pct(104.0, 100.0) == pytest.approx(4.0)
```

- [ ] **Step 2: Fehlschlag verifizieren**

Run: `.venv/bin/pytest tests/test_indicators.py -v` — Expected: FAIL (`ModuleNotFoundError` bzw. `AttributeError`).

- [ ] **Step 3: Implementieren** — `trainspotter/indicators.py`:

```python
import pandas as pd
import trainspotter.config as cfg

def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()

def volume_buildup_ratio(volumes: pd.Series, recent_days: int = cfg.RECENT_VOL_DAYS,
                         baseline_days: int = cfg.BASELINE_VOL_DAYS) -> float:
    if len(volumes) < recent_days + baseline_days:
        return 0.0
    recent = volumes.iloc[-recent_days:].mean()
    baseline = volumes.iloc[-(recent_days + baseline_days):-recent_days].mean()
    return float(recent / baseline) if baseline > 0 else 0.0

def adr_pct(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20) -> float:
    rng = (high - low) / close * 100.0
    return float(rng.iloc[-window:].mean())

def relative_strength(stock_close: pd.Series, index_close: pd.Series, days: int) -> float:
    if len(stock_close) < days + 1 or len(index_close) < days + 1:
        return 0.0
    s = (stock_close.iloc[-1] / stock_close.iloc[-days - 1] - 1) * 100
    i = (index_close.iloc[-1] / index_close.iloc[-days - 1] - 1) * 100
    return float(s - i)

def breakout_level(high: pd.Series, window: int = cfg.BREAKOUT_WINDOW) -> float:
    """Hoechstes Hoch der letzten `window` Tage OHNE den letzten (= heutigen) Tag."""
    return float(high.iloc[-(window + 1):-1].max())

def time_prorated_volume_ratio(volume_today: float, avg_daily_volume: float,
                               elapsed_frac: float) -> float:
    expected = avg_daily_volume * max(elapsed_frac, 0.05)
    return float(volume_today / expected) if expected > 0 else 0.0

def distance_pct(price: float, level: float) -> float:
    return (price / level - 1) * 100.0
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_indicators.py -v` — Expected: 8 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Indikatoren mit handgerechneten Tests"`

---

### Task 3: Zustandsverwaltung

**Files:**
- Create: `trainspotter/state.py`, `tests/test_state.py`

**Interfaces:**
- Produces: `load_json(path, default)`, `save_json(path, data)` (atomar), `append_trade(csv_path, trade: dict)` (feste Spalten `TRADE_FIELDS`), `load_trades(csv_path) -> list[dict]`, `commit_and_push(paths: list[str], message: str) -> bool` (No-Op bei `TRAINSPOTTER_NO_GIT=1`; sonst add→commit→pull --rebase→push mit 3 Versuchen)
- `TRADE_FIELDS = ["id","ticker","market","liste","score","criteria","opened","closed","entry","exit","qty","pnl_eur","pnl_pct","reason"]`

- [ ] **Step 1: Failing Tests** — `tests/test_state.py`:

```python
import json, os
from trainspotter import state

def test_save_load_roundtrip(tmp_path):
    p = str(tmp_path / "x.json")
    state.save_json(p, {"a": 1})
    assert state.load_json(p, {}) == {"a": 1}

def test_load_defekte_datei_gibt_default(tmp_path):
    p = tmp_path / "kaputt.json"
    p.write_text("{nicht json")
    assert state.load_json(str(p), {"ok": True}) == {"ok": True}

def test_load_fehlende_datei_gibt_default(tmp_path):
    assert state.load_json(str(tmp_path / "fehlt.json"), []) == []

def test_append_und_load_trades(tmp_path):
    p = str(tmp_path / "trades.csv")
    t = {f: "" for f in state.TRADE_FIELDS} | {"id": "NVDA-2026-07-08", "pnl_eur": "12.5"}
    state.append_trade(p, t)
    state.append_trade(p, t | {"id": "SAP-2026-07-08"})
    rows = state.load_trades(p)
    assert len(rows) == 2 and rows[0]["id"] == "NVDA-2026-07-08"

def test_commit_noop_ohne_git(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAINSPOTTER_NO_GIT", "1")
    assert state.commit_and_push(["egal.json"], "msg") is True
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_state.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren** — `trainspotter/state.py`:

```python
import csv, json, os, subprocess

TRADE_FIELDS = ["id", "ticker", "market", "liste", "score", "criteria", "opened",
                "closed", "entry", "exit", "qty", "pnl_eur", "pnl_pct", "reason"]

def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)   # atomar: nie halb geschriebene Zustandsdatei

def append_trade(csv_path, trade: dict):
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    new = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TRADE_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(trade)

def load_trades(csv_path) -> list[dict]:
    try:
        with open(csv_path, newline="") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []

def commit_and_push(paths: list[str], message: str) -> bool:
    if os.environ.get("TRAINSPOTTER_NO_GIT") == "1":
        return True
    subprocess.run(["git", "add", *paths], check=False)
    r = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
    if r.returncode != 0:                      # nichts zu committen
        return True
    for _ in range(3):
        subprocess.run(["git", "pull", "--rebase"], check=False)
        if subprocess.run(["git", "push"], capture_output=True).returncode == 0:
            return True
    return False
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_state.py -v` — Expected: 5 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Zustandsverwaltung (JSON atomar, Trades-CSV, Git-Sync)"`

---

### Task 4: Börsenkalender

**Files:**
- Create: `trainspotter/calendar_utils.py`, `tests/test_calendar.py`

**Interfaces:**
- Produces: `is_trading_day(d: datetime.date, market: str) -> bool`, `session_bounds(d, market) -> tuple[datetime, datetime]` (tz-aware, US: 09:30–16:00 New York, EU: 09:00–17:30 Berlin), `elapsed_fraction(now_utc, market) -> float` (0..1), `should_poll_commands(now_utc, market) -> bool` (US: immer; EU: nur vor 15:15 Berlin — danach übernimmt der US-Beobachter, sonst klauen sich zwei Poller die Telegram-Updates)

- [ ] **Step 1: Failing Tests** — `tests/test_calendar.py`:

```python
from datetime import date, datetime, timezone
from trainspotter import calendar_utils as cal

def test_wochenende_und_feiertage():
    assert not cal.is_trading_day(date(2026, 7, 11), "us")      # Samstag
    assert not cal.is_trading_day(date(2026, 7, 3), "us")       # 4.Juli beobachtet
    assert cal.is_trading_day(date(2026, 7, 3), "eu")           # DE offen
    assert not cal.is_trading_day(date(2026, 4, 6), "eu")       # Ostermontag
    assert cal.is_trading_day(date(2026, 7, 8), "us")

def test_session_bounds_eu():
    o, c = cal.session_bounds(date(2026, 7, 8), "eu")
    assert (o.hour, o.minute) == (9, 0) and (c.hour, c.minute) == (17, 30)

def test_elapsed_fraction_mitte():
    # 12:00 UTC = 14:00 Berlin -> 5h von 8.5h EU-Sitzung
    now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
    assert abs(cal.elapsed_fraction(now, "eu") - 5 / 8.5) < 0.01

def test_should_poll_commands():
    vor = datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc)    # 12:00 Berlin
    nach = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)   # 16:00 Berlin
    assert cal.should_poll_commands(vor, "eu")
    assert not cal.should_poll_commands(nach, "eu")
    assert cal.should_poll_commands(nach, "us")
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_calendar.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren** — `trainspotter/calendar_utils.py`:

```python
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

TZ = {"us": ZoneInfo("America/New_York"), "eu": ZoneInfo("Europe/Berlin")}
OPEN_CLOSE = {"us": (time(9, 30), time(16, 0)), "eu": (time(9, 0), time(17, 30))}

US_HOLIDAYS_2026 = {"2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
                    "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25"}
DE_HOLIDAYS_2026 = {"2026-01-01", "2026-04-03", "2026-04-06", "2026-05-01", "2026-05-25",
                    "2026-12-24", "2026-12-25", "2026-12-31"}
HOLIDAYS = {"us": US_HOLIDAYS_2026, "eu": DE_HOLIDAYS_2026}

def is_trading_day(d: date, market: str) -> bool:
    return d.weekday() < 5 and d.isoformat() not in HOLIDAYS[market]

def session_bounds(d: date, market: str):
    tz = TZ[market]
    o, c = OPEN_CLOSE[market]
    return datetime.combine(d, o, tz), datetime.combine(d, c, tz)

def elapsed_fraction(now_utc: datetime, market: str) -> float:
    local = now_utc.astimezone(TZ[market])
    o, c = session_bounds(local.date(), market)
    total = (c - o).total_seconds()
    return min(max((local - o).total_seconds() / total, 0.0), 1.0)

def should_poll_commands(now_utc: datetime, market: str) -> bool:
    if market == "us":
        return True
    return now_utc.astimezone(TZ["eu"]).time() < time(15, 15)
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_calendar.py -v` — Expected: 4 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Boersenkalender US/DE 2026 mit Sitzungszeiten"`

Hinweis für den Umsetzer: Die Feiertagslisten gelten für 2026 und müssen jährlich gepflegt werden — steht als Punkt in der README (Task 18).

---

### Task 5: Universum

**Files:**
- Create: `trainspotter/universe.py`, `config/universe_de.csv`, `tests/test_universe.py`, `tests/fixtures/nasdaqlisted_sample.txt`

**Interfaces:**
- Produces: `parse_nasdaq_file(text: str) -> list[str]`, `load_us_universe() -> list[str]` (lädt Symbol-Dateien von nasdaqtrader.com), `load_de_universe() -> list[str]` (aus `config/universe_de.csv`, Ticker mit `.DE`-Suffix)

- [ ] **Step 1: Fixture + Failing Tests**

`tests/fixtures/nasdaqlisted_sample.txt` (Originalformat von nasdaqtrader.com):
```
Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
AAPL|Apple Inc. - Common Stock|Q|N|N|100|N|N
ZTST|Test Symbol|Q|Y|N|100|N|N
QQQ|Invesco QQQ Trust|G|N|N|100|Y|N
NVDA|NVIDIA Corporation - Common Stock|Q|N|N|100|N|N
File Creation Time: 0707202622:30|||||||
```

`tests/test_universe.py`:
```python
from pathlib import Path
from trainspotter import universe

def test_parse_nasdaq_ohne_testissues_und_etfs():
    text = Path("tests/fixtures/nasdaqlisted_sample.txt").read_text()
    syms = universe.parse_nasdaq_file(text)
    assert syms == ["AAPL", "NVDA"]          # kein Test-Issue, kein ETF, keine Fusszeile

def test_de_universe_laedt_und_hat_de_suffix():
    syms = universe.load_de_universe()
    assert len(syms) >= 40 and all(s.endswith(".DE") for s in syms)
    assert "SAP.DE" in syms
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_universe.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren**

`config/universe_de.csv` (V1 = DAX 40 + TecDAX-Auswahl; MDAX/SDAX ist bewusst V2 — in README-Backlog):
```
ticker
ADS.DE
AIR.DE
ALV.DE
BAS.DE
BAYN.DE
BEI.DE
BMW.DE
BNR.DE
CBK.DE
CON.DE
1COV.DE
DTG.DE
DHL.DE
DBK.DE
DB1.DE
DTE.DE
EOAN.DE
FRE.DE
HNR1.DE
HEI.DE
HEN3.DE
IFX.DE
MBG.DE
MRK.DE
MTX.DE
MUV2.DE
P911.DE
PAH3.DE
QIA.DE
RHM.DE
RWE.DE
SAP.DE
SRT3.DE
SIE.DE
ENR.DE
SHL.DE
SY1.DE
VNA.DE
VOW3.DE
ZAL.DE
AIXA.DE
BC8.DE
EVT.DE
JEN.DE
NEM.DE
S92.DE
TMV.DE
UTDI.DE
WAF.DE
SOW.DE
```

`trainspotter/universe.py`:
```python
import csv, requests

NASDAQ_URLS = ["https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
               "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"]

def parse_nasdaq_file(text: str) -> list[str]:
    syms = []
    for line in text.splitlines()[1:]:                 # Kopfzeile weg
        parts = line.split("|")
        if len(parts) < 7 or line.startswith("File Creation"):
            continue
        sym, test_issue, etf = parts[0], parts[3], parts[6]
        if test_issue == "N" and etf == "N" and sym.isalpha():
            syms.append(sym)
    return syms

def load_us_universe() -> list[str]:
    syms: list[str] = []
    for url in NASDAQ_URLS:
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            syms += parse_nasdaq_file(r.text)
        except requests.RequestException:
            continue                                   # eine Quelle darf ausfallen
    return sorted(set(syms))

def load_de_universe(path: str = "config/universe_de.csv") -> list[str]:
    with open(path, newline="") as f:
        return [row["ticker"] for row in csv.DictReader(f)]
```

Hinweis: `otherlisted.txt` nutzt `ACT Symbol` in Spalte 0 und hat kein ETF-Feld an Position 6 in identischer Bedeutung — der Parser filtert dort ggf. zu streng, das ist akzeptabel (lieber weniger als kaputte Symbole).

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_universe.py -v` — Expected: 2 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Universum US (NASDAQ Trader) + DE-Liste"`

---

### Task 6: Datenschicht (Yahoo + Finnhub)

**Files:**
- Create: `trainspotter/data/__init__.py`, `trainspotter/data/yahoo.py`, `trainspotter/data/finnhub.py`, `tests/test_data.py`

**Interfaces:**
- Produces `data/yahoo.py`: `daily_history(tickers: list[str], period="2y") -> dict[str, pd.DataFrame]` (Spalten Open/High/Low/Close/Volume, je Ticker; kranke Ticker fehlen einfach), `split_batch(df, tickers) -> dict[str, pd.DataFrame]` (pure, testbar), `intraday_snapshot(tickers) -> dict[str, dict]` (je Ticker `{"price": float, "day_volume": float}` aus 15-Min-Kerzen von heute, ~15 Min. verzögert), `index_change_pct(market: str) -> float` (Intraday vs. Vortagesschluss), `top_movers_us(limit=25) -> list[str]`, `headlines(ticker, limit=5) -> list[str]`
- Produces `data/finnhub.py`: Klasse `Finnhub(api_key)` mit `quote(ticker) -> dict | None` (`{"price": c}`; Echtzeit US; Ratenbremse ≥1s zwischen Aufrufen). **Achtung: Finnhub-/quote liefert KEIN Volumen** — Volumen kommt im US-Betrieb aus dem Yahoo-Intraday-Cache (Task 13).

- [ ] **Step 1: Failing Tests** — `tests/test_data.py`:

```python
import pandas as pd
from trainspotter.data import yahoo, finnhub

def _batch_df():
    cols = pd.MultiIndex.from_product([["AAA", "BBB"], ["Open", "High", "Low", "Close", "Volume"]])
    data = [[1, 2, 0.5, 1.5, 100, 10, 20, 5, 15, 1000]] * 3
    return pd.DataFrame(data, columns=cols)

def test_split_batch():
    out = yahoo.split_batch(_batch_df(), ["AAA", "BBB", "CCC"])
    assert set(out) == {"AAA", "BBB"}                    # CCC fehlt -> weggelassen
    assert list(out["AAA"].columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert out["BBB"]["Close"].iloc[-1] == 15

def test_finnhub_quote_parst_antwort(monkeypatch):
    fh = finnhub.Finnhub("key", min_interval=0)
    monkeypatch.setattr(fh, "_get", lambda path, params: {"c": 101.5, "pc": 100.0})
    assert fh.quote("NVDA") == {"price": 101.5}

def test_finnhub_quote_none_bei_fehler(monkeypatch):
    fh = finnhub.Finnhub("key", min_interval=0)
    monkeypatch.setattr(fh, "_get", lambda path, params: None)
    assert fh.quote("NVDA") is None
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_data.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren**

`trainspotter/data/__init__.py`: leer.

`trainspotter/data/yahoo.py`:
```python
"""Einzige Stelle im Projekt, die yfinance importiert (austauschbare Quelle)."""
import pandas as pd
import yfinance as yf
import trainspotter.config as cfg

def split_batch(df: pd.DataFrame, tickers: list[str]) -> dict[str, pd.DataFrame]:
    out = {}
    if df is None or df.empty:
        return out
    for t in tickers:
        try:
            sub = df[t].dropna(how="all") if isinstance(df.columns, pd.MultiIndex) else df
            if not sub.empty and "Close" in sub:
                out[t] = sub[["Open", "High", "Low", "Close", "Volume"]]
        except (KeyError, IndexError):
            continue
    return out

def daily_history(tickers: list[str], period: str = "2y") -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), 400):               # Batches gegen Timeouts
        chunk = tickers[i:i + 400]
        try:
            df = yf.download(chunk, period=period, interval="1d", group_by="ticker",
                             auto_adjust=True, progress=False, threads=True)
            out.update(split_batch(df, chunk))
        except Exception:
            continue                                     # Batch darf ausfallen
    return out

def intraday_snapshot(tickers: list[str]) -> dict[str, dict]:
    try:
        df = yf.download(tickers, period="1d", interval="15m", group_by="ticker",
                         auto_adjust=True, progress=False, threads=True)
    except Exception:
        return {}
    out = {}
    for t, sub in split_batch(df, tickers).items():
        out[t] = {"price": float(sub["Close"].iloc[-1]),
                  "day_volume": float(sub["Volume"].sum())}
    return out

def index_change_pct(market: str) -> float:
    try:
        h = yf.Ticker(cfg.INDEX_SYMBOL[market]).history(period="2d", interval="1d")
        prev, last = float(h["Close"].iloc[-2]), float(h["Close"].iloc[-1])
        return (last / prev - 1) * 100.0
    except Exception:
        return 0.0                                       # neutral bei Datenausfall

def top_movers_us(limit: int = 25) -> list[str]:
    try:
        r = yf.screen("day_gainers", count=limit)
        return [q["symbol"] for q in r.get("quotes", [])]
    except Exception:
        return []

def headlines(ticker: str, limit: int = 5) -> list[str]:
    try:
        news = yf.Ticker(ticker).news or []
        return [n.get("content", {}).get("title") or n.get("title", "") for n in news[:limit]]
    except Exception:
        return []
```

`trainspotter/data/finnhub.py`:
```python
import time
import requests

class Finnhub:
    BASE = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str, min_interval: float = 1.05):
        self.key = api_key
        self.min_interval = min_interval    # 60 Aufrufe/Min Gratis-Limit
        self._last = 0.0

    def _get(self, path: str, params: dict) -> dict | None:
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()
        try:
            r = requests.get(f"{self.BASE}{path}", params=params | {"token": self.key}, timeout=10)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            return None

    def quote(self, ticker: str) -> dict | None:
        d = self._get("/quote", {"symbol": ticker})
        if not d or not d.get("c"):
            return None
        return {"price": float(d["c"])}
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_data.py -v` — Expected: 3 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Datenschicht Yahoo (Batch/Intraday/Movers/News) + Finnhub-Echtzeitquotes"`

---

### Task 7: Nacht-Scan (Bahnsteig-Score)

**Files:**
- Create: `trainspotter/night_scan.py`, `tests/test_night_scan.py`

**Interfaces:**
- Consumes: `indicators.*`, `cfg.*`
- Produces: `platform_score(ticker: str, df: pd.DataFrame, index_close: pd.Series, market: str) -> dict | None` und `build_watchlist(entries: list[dict]) -> list[dict]` (Score absteigend, max. `WATCHLIST_SIZE`).
- Watchlist-Eintrag (Format für alle Folgetasks): `{"ticker": str, "market": "us"|"eu", "liste": "konservativ"|"spekulativ", "score": int, "breakout_level": float, "adr_pct": float, "avg_volume": float, "criteria": list[str]}`
- Punktevergabe: Volumen-Aufbau ≥1,5× → 25 | nahe Ausbruch (−5 %..+1 %) → 25 | Trend intakt (Kurs>SMA20>SMA50, SMA20 steigend) → 20 | rel. Stärke >5 pp → 20 (>0 → 10). Qualifikation ab `SCORE_MIN=60`. Kurs >1 % über Widerstand → ganz raus (schon abgefahren).

- [ ] **Step 1: Failing Tests** — `tests/test_night_scan.py`:

```python
import pandas as pd
from trainspotter import night_scan

def _df(n=80, vol_last5=2_000_000):
    close = pd.Series([100 + 0.3 * i for i in range(n)])
    return pd.DataFrame({"Open": close - 0.1, "High": close + 1, "Low": close - 1,
                         "Close": close,
                         "Volume": [1_000_000] * (n - 5) + [vol_last5] * 5})

def test_platform_score_kandidat():
    e = night_scan.platform_score("TTT", _df(), pd.Series([100.0] * 80), "us")
    # 25 (Volumen 2x) + 25 (0.6% unter 20T-Hoch) + 20 (Trend) + 20 (RS ~17pp) = 90
    assert e["score"] == 90
    assert e["liste"] == "konservativ"           # ADR ~1.7%
    assert e["breakout_level"] == 124.4          # Hoch von Tag n-2: 100+0.3*78+1
    assert e["avg_volume"] > 0 and len(e["criteria"]) == 4

def test_pennystock_fliegt_raus():
    df = _df()
    df[["Open", "High", "Low", "Close"]] = df[["Open", "High", "Low", "Close"]] / 100.0
    assert night_scan.platform_score("PNY", df, pd.Series([100.0] * 80), "us") is None

def test_zu_wenig_score_fliegt_raus():
    df = _df(vol_last5=1_000_000)                # kein Volumen-Aufbau
    df["Close"] = 100.0                          # kein Trend, weit unterm Hoch? ->
    df["High"] = 130.0                           # 23% unterm 20T-Hoch -> keine Naehe-Punkte
    assert night_scan.platform_score("LAME", df, pd.Series([100.0] * 80), "us") is None

def test_build_watchlist_sortiert_und_kappt():
    entries = [{"score": s, "ticker": f"T{s}"} for s in (70, 95, 80)]
    wl = night_scan.build_watchlist(entries)
    assert [e["score"] for e in wl] == [95, 80, 70]
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_night_scan.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren** — `trainspotter/night_scan.py`:

```python
import pandas as pd
import trainspotter.config as cfg
from trainspotter import indicators as ind

def platform_score(ticker: str, df: pd.DataFrame, index_close: pd.Series, market: str) -> dict | None:
    if df is None or len(df) < 60:
        return None
    close = df["Close"]
    price = float(close.iloc[-1])
    dollar_vol = float((close * df["Volume"]).iloc[-20:].mean())
    if price < cfg.MIN_PRICE or dollar_vol < cfg.MIN_DOLLAR_VOLUME:
        return None
    adr = ind.adr_pct(df["High"], df["Low"], close)
    if adr >= cfg.ADR_MIN_SPEC:
        liste = "spekulativ"
    elif adr >= cfg.ADR_MIN_KONS:
        liste = "konservativ"
    else:
        return None                                      # bewegt sich historisch nicht
    level = ind.breakout_level(df["High"])
    dist = ind.distance_pct(price, level)
    if dist > cfg.MAX_ABOVE_BREAKOUT_PCT:
        return None                                      # Zug gestern schon abgefahren
    score, criteria = 0, []
    vb = ind.volume_buildup_ratio(df["Volume"])
    if vb >= cfg.VOL_BUILDUP_RATIO:
        score += 25; criteria.append(f"volumen_aufbau:{vb:.1f}x")
    if dist >= -cfg.NEAR_BREAKOUT_PCT:
        score += 25; criteria.append(f"nahe_ausbruch:{dist:.1f}%")
    sma20, sma50 = ind.sma(close, 20), ind.sma(close, 50)
    if price > sma20.iloc[-1] > sma50.iloc[-1] and sma20.iloc[-1] > sma20.iloc[-6]:
        score += 20; criteria.append("trend_intakt")
    rs = ind.relative_strength(close, index_close, cfg.RS_DAYS)
    if rs > 5:
        score += 20; criteria.append(f"rel_staerke:+{rs:.0f}pp")
    elif rs > 0:
        score += 10; criteria.append(f"rel_staerke:+{rs:.0f}pp")
    if score < cfg.SCORE_MIN:
        return None
    return {"ticker": ticker, "market": market, "liste": liste, "score": score,
            "breakout_level": round(level, 4), "adr_pct": round(adr, 2),
            "avg_volume": float(df["Volume"].iloc[-20:].mean()), "criteria": criteria}

def build_watchlist(entries: list[dict]) -> list[dict]:
    return sorted(entries, key=lambda e: e["score"], reverse=True)[:cfg.WATCHLIST_SIZE]
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_night_scan.py -v` — Expected: 4 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Nacht-Scan mit Bahnsteig-Score und Watchlist"`

---

### Task 8: Trigger-Logik

**Files:**
- Create: `trainspotter/triggers.py`, `tests/test_triggers.py`

**Interfaces:**
- Consumes: Watchlist-Eintrag (Task 7), `indicators.time_prorated_volume_ratio/distance_pct`
- Produces: `check_trigger(entry: dict, price: float, day_volume: float, index_change_pct: float, elapsed_frac: float, today: str) -> dict | None` — Ergebnis: `{"id": "TICKER-YYYY-MM-DD", "ticker", "market", "liste", "score", "status": "alert"|"missed", "price", "entry", "stop", "target1", "breakout_level", "vol_ratio", "dist_pct", "reasons": list[str], "warning": str|None}`
- `apply_alert_discipline(candidates: list[dict], alerts_sent: set[str], sent_counts: dict[str, int]) -> list[dict]` — dedupliziert per id, kappt `status=="alert"` auf `MAX_ALERTS_PER_LIST` je Liste (Score absteigend, bereits Gesendetes zählt mit); `missed` wird nur dedupliziert.

- [ ] **Step 1: Failing Tests** — `tests/test_triggers.py`:

```python
import pytest
from trainspotter import triggers

ENTRY = {"ticker": "NVDA", "market": "us", "liste": "spekulativ", "score": 90,
         "breakout_level": 100.0, "adr_pct": 4.0, "avg_volume": 1_000_000,
         "criteria": ["volumen_aufbau:2.0x"]}

def _check(price, vol=600_000, idx=-0.5, entry=ENTRY):
    return triggers.check_trigger(entry, price, vol, idx, 0.3, "2026-07-08")

def test_alert_mit_stop_und_ziel():
    r = _check(101.5)
    assert r["status"] == "alert" and r["id"] == "NVDA-2026-07-08"
    assert r["vol_ratio"] == pytest.approx(2.0)          # 600k / (1M * 0.3)
    assert r["stop"] == pytest.approx(94.0)              # 100 * (1 - 6%)
    assert r["target1"] == pytest.approx(111.65)         # 101.5 * 1.10
    assert r["warning"] is None

def test_kein_ausbruch_kein_alert():
    assert _check(99.5) is None

def test_ohne_volumen_geisterzug():
    assert _check(101.5, vol=250_000) is None            # Ratio 0.83 < 2.0

def test_zug_verpasst():
    assert _check(107.0)["status"] == "missed"           # +7% > 6%-Grenze spek.

def test_marktfilter():
    kons = ENTRY | {"liste": "konservativ", "adr_pct": 2.0}
    assert triggers.check_trigger(kons, 101.5, 600_000, -2.0, 0.3, "2026-07-08") is None
    r = _check(101.5, idx=-2.0)                          # spekulativ: Warnung statt Blockade
    assert "Gegenwind" in r["warning"]

def test_alert_disziplin():
    cands = [dict(ENTRY, breakout_level=100.0) | {"id": f"T{i}-d", "status": "alert",
             "score": 60 + i, "liste": "spekulativ"} for i in range(7)]
    out = triggers.apply_alert_discipline(cands, alerts_sent={"T6-d"}, sent_counts={"spekulativ": 2})
    ids = [c["id"] for c in out]
    assert "T6-d" not in ids                             # schon gesendet
    assert len(ids) == 3                                 # 5 Budget - 2 verbraucht
    assert ids == ["T5-d", "T4-d", "T3-d"]               # beste Scores zuerst
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_triggers.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren** — `trainspotter/triggers.py`:

```python
import trainspotter.config as cfg
from trainspotter import indicators as ind

def check_trigger(entry: dict, price: float, day_volume: float, index_change_pct: float,
                  elapsed_frac: float, today: str) -> dict | None:
    level, liste = entry["breakout_level"], entry["liste"]
    if price <= level:
        return None
    vol_ratio = ind.time_prorated_volume_ratio(day_volume, entry["avg_volume"], elapsed_frac)
    if vol_ratio < cfg.TRIGGER_VOL_RATIO:
        return None                                      # Geisterzug
    warning = None
    if index_change_pct < cfg.INDEX_FILTER_PCT:
        if liste == "konservativ":
            return None
        warning = f"Markt-Gegenwind: Index {index_change_pct:.1f}% heute"
    dist = ind.distance_pct(price, level)
    status = "missed" if dist > cfg.MISSED_TRAIN_PCT[liste] else "alert"
    return {"id": f"{entry['ticker']}-{today}", "ticker": entry["ticker"],
            "market": entry["market"], "liste": liste, "score": entry["score"],
            "status": status, "price": price, "entry": price,
            "stop": round(level * (1 - cfg.STOP_PCT[liste] / 100), 4),
            "target1": round(price * (1 + cfg.TARGET1_PCT[liste] / 100), 4),
            "breakout_level": level, "vol_ratio": round(vol_ratio, 2),
            "dist_pct": round(dist, 2),
            "reasons": entry["criteria"] + [f"ausbruch_ueber:{level:.2f}",
                                            f"volumen:{vol_ratio:.1f}x_zeitanteilig"],
            "warning": warning}

def apply_alert_discipline(candidates: list[dict], alerts_sent: set[str],
                           sent_counts: dict[str, int]) -> list[dict]:
    fresh = [c for c in candidates if c["id"] not in alerts_sent]
    out = [c for c in fresh if c["status"] == "missed"]
    budget = {l: cfg.MAX_ALERTS_PER_LIST - sent_counts.get(l, 0) for l in cfg.LISTEN}
    for c in sorted((c for c in fresh if c["status"] == "alert"),
                    key=lambda c: c["score"], reverse=True):
        if budget[c["liste"]] > 0:
            budget[c["liste"]] -= 1
            out.append(c)
    return out
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_triggers.py -v` — Expected: 6 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Live-Trigger mit Volumen-, Markt- und Disziplin-Regeln"`

---

### Task 9: Paper-Trading

**Files:**
- Create: `trainspotter/paper_trading.py`, `tests/test_paper_trading.py`

**Interfaces:**
- Consumes: Trigger-Ergebnis (Task 8), `state.TRADE_FIELDS`
- Produces: `open_position(alert: dict, now_iso: str) -> dict`, `update_position(pos: dict, price: float, now_iso: str, session_close: bool = False) -> tuple[list[str], dict | None]` (Events z.B. `["stop"]`, `["target1", "trail"]`; zweites Element = Trade-Record wenn Position geschlossen), Position-Dict: `{"id","ticker","market","liste","score","criteria","entry","qty","stop","target1","half_booked","realized","trail_prices","opened","open_days"}`
- Regeln: Einstieg = Alert-Kurs × (1+0,2 %); Stop erreicht → alles zu; Ziel 1 → halbe Position verbucht, Stop danach = max(alt, 30-Min-Tief × (1−0,5 %)); `session_close=True`: spekulativ immer zu, konservativ nach 3 Handelstagen.

- [ ] **Step 1: Failing Tests** — `tests/test_paper_trading.py`:

```python
import pytest
from trainspotter import paper_trading as pt

ALERT = {"id": "NVDA-2026-07-08", "ticker": "NVDA", "market": "us", "liste": "spekulativ",
         "score": 90, "status": "alert", "price": 100.0, "entry": 100.0,
         "stop": 94.0, "target1": 110.0, "breakout_level": 100.0, "vol_ratio": 2.5,
         "dist_pct": 1.0, "reasons": ["r1"], "warning": None}

def test_open_mit_slippage():
    pos = pt.open_position(ALERT, "2026-07-08T16:00:00+00:00")
    assert pos["entry"] == pytest.approx(100.2)
    assert pos["qty"] == pytest.approx(1000.0 / 100.2)

def test_stop_schliesst_alles():
    pos = pt.open_position(ALERT, "2026-07-08T16:00:00+00:00")
    events, trade = pt.update_position(pos, 93.5, "2026-07-08T16:30:00+00:00")
    assert events == ["stop"] and trade["reason"] == "stop"
    # trade["pnl_eur"] ist auf 2 Stellen gerundet -> abs-Toleranz noetig
    assert float(trade["pnl_eur"]) == pytest.approx((1000.0 / 100.2) * (93.5 - 100.2), abs=0.01)

def test_ziel1_bucht_haelfte_und_trailt():
    pos = pt.open_position(ALERT, "2026-07-08T16:00:00+00:00")
    events, trade = pt.update_position(pos, 110.5, "2026-07-08T17:00:00+00:00")
    assert "target1" in events and trade is None
    assert pos["half_booked"] and pos["qty"] == pytest.approx(1000.0 / 100.2 / 2)
    assert pos["realized"] == pytest.approx((1000.0 / 100.2 / 2) * (110.0 - 100.2))
    assert pos["stop"] == pytest.approx(110.5 * 0.995)   # Trailing unterm 30-Min-Tief
    # naechster Tick faellt unter den Trail -> Rest zu, Gesamt-PnL = realisiert + Rest
    events2, trade2 = pt.update_position(pos, 109.0, "2026-07-08T17:02:00+00:00")
    assert events2 == ["stop"] and trade2["reason"] == "trail_stop"

def test_session_close_spekulativ():
    pos = pt.open_position(ALERT, "2026-07-08T16:00:00+00:00")
    events, trade = pt.update_position(pos, 103.0, "2026-07-08T20:00:00+00:00", session_close=True)
    assert trade["reason"] == "tagesschluss"

def test_session_close_konservativ_haelt_3_tage():
    pos = pt.open_position(dict(ALERT, liste="konservativ"), "2026-07-08T10:00:00+00:00")
    for day in (8, 9):
        _, trade = pt.update_position(pos, 101.0, f"2026-07-{day:02d}T15:30:00+00:00", session_close=True)
        assert trade is None
    _, trade = pt.update_position(pos, 101.0, "2026-07-10T15:30:00+00:00", session_close=True)
    assert trade["reason"] == "max_haltedauer"
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_paper_trading.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren** — `trainspotter/paper_trading.py`:

```python
from datetime import datetime, timedelta
import trainspotter.config as cfg

def open_position(alert: dict, now_iso: str) -> dict:
    entry = alert["entry"] * (1 + cfg.SLIPPAGE_PCT / 100)
    return {"id": alert["id"], "ticker": alert["ticker"], "market": alert["market"],
            "liste": alert["liste"], "score": alert["score"],
            "criteria": "|".join(alert["reasons"]), "entry": entry,
            "qty": cfg.POSITION_SIZE_EUR / entry, "stop": alert["stop"],
            "target1": alert["target1"], "half_booked": False, "realized": 0.0,
            "trail_prices": [], "opened": now_iso, "open_days": 0}

def _close(pos: dict, price: float, reason: str, now_iso: str) -> dict:
    pnl = pos["realized"] + pos["qty"] * (price - pos["entry"])
    return {"id": pos["id"], "ticker": pos["ticker"], "market": pos["market"],
            "liste": pos["liste"], "score": pos["score"], "criteria": pos["criteria"],
            "opened": pos["opened"], "closed": now_iso,
            "entry": round(pos["entry"], 4), "exit": round(price, 4),
            "qty": round(pos["qty"], 4), "pnl_eur": round(pnl, 2),
            "pnl_pct": round(pnl / cfg.POSITION_SIZE_EUR * 100, 2), "reason": reason}

def _trail_low(pos: dict, now: datetime) -> float:
    cutoff = (now - timedelta(minutes=cfg.TRAIL_WINDOW_MIN)).isoformat()
    pos["trail_prices"] = [(t, p) for t, p in pos["trail_prices"] if t >= cutoff]
    return min(p for _, p in pos["trail_prices"])

def update_position(pos: dict, price: float, now_iso: str,
                    session_close: bool = False) -> tuple[list[str], dict | None]:
    now = datetime.fromisoformat(now_iso)
    pos["trail_prices"].append((now_iso, price))
    events: list[str] = []
    if price <= pos["stop"]:
        reason = "trail_stop" if pos["half_booked"] else "stop"
        return ["stop"], _close(pos, price, reason, now_iso)
    if not pos["half_booked"] and price >= pos["target1"]:
        half = pos["qty"] / 2
        pos["realized"] += half * (pos["target1"] - pos["entry"])
        pos["qty"], pos["half_booked"] = half, True
        events.append("target1")
    if pos["half_booked"]:
        new_stop = _trail_low(pos, now) * (1 - cfg.TRAIL_BUFFER_PCT / 100)
        if new_stop > pos["stop"]:
            pos["stop"] = round(new_stop, 4)
            events.append("trail")
    if session_close:
        if pos["liste"] == "spekulativ":
            return events + ["session_close"], _close(pos, price, "tagesschluss", now_iso)
        pos["open_days"] += 1
        if pos["open_days"] >= cfg.MAX_HOLD_DAYS_KONS:
            return events + ["session_close"], _close(pos, price, "max_haltedauer", now_iso)
    return events, None
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_paper_trading.py -v` — Expected: 5 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Paper-Trading mit Slippage, Ziel-1-Teilverkauf und Trailing-Stop"`

---

### Task 10: Telegram-Bot

**Files:**
- Create: `trainspotter/telegram_bot.py`, `tests/test_telegram.py`

**Interfaces:**
- Produces: `send_message(text: str) -> bool` (Env `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`; 3 Versuche; `False` statt Exception), `poll_commands(offset: int) -> tuple[list[str], int]` (getUpdates, timeout=0), `format_alert(alert: dict, ki: dict | None) -> str`, `format_update(event: str, pos: dict, price: float) -> str`, `format_trade_closed(trade: dict) -> str`
- Alert-Format (golden, exakt):

```
🚂 ZUG ERKANNT — NVDA [spekulativ]
Regeln: volumen_aufbau:2.0x, ausbruch_ueber:100.00, volumen:2.5x_zeitanteilig
Ausbruch über 100.00 | Kurs 101.50 (+1.5%)
Einstieg: 101.50 | Stop: 94.00 | Ziel 1: 111.65
Danach: Trailing-Stop.
KI: Ausbruch wird von News getragen.
```

- [ ] **Step 1: Failing Tests** — `tests/test_telegram.py`:

```python
from trainspotter import telegram_bot as tg

ALERT = {"id": "NVDA-2026-07-08", "ticker": "NVDA", "liste": "spekulativ", "status": "alert",
         "price": 101.5, "entry": 101.5, "stop": 94.0, "target1": 111.65,
         "breakout_level": 100.0, "vol_ratio": 2.5, "dist_pct": 1.5,
         "reasons": ["volumen_aufbau:2.0x", "ausbruch_ueber:100.00", "volumen:2.5x_zeitanteilig"],
         "warning": None, "market": "us", "score": 90}

def test_format_alert_golden():
    text = tg.format_alert(ALERT, {"einschaetzung": "Ausbruch wird von News getragen."})
    assert text == ("🚂 ZUG ERKANNT — NVDA [spekulativ]\n"
                    "Regeln: volumen_aufbau:2.0x, ausbruch_ueber:100.00, volumen:2.5x_zeitanteilig\n"
                    "Ausbruch über 100.00 | Kurs 101.50 (+1.5%)\n"
                    "Einstieg: 101.50 | Stop: 94.00 | Ziel 1: 111.65\n"
                    "Danach: Trailing-Stop.\n"
                    "KI: Ausbruch wird von News getragen.")

def test_format_alert_verpasst_und_warnung():
    a = ALERT | {"status": "missed", "dist_pct": 7.0, "warning": "Markt-Gegenwind: Index -2.0% heute"}
    text = tg.format_alert(a, None)
    assert text.startswith("🚂💨 ZUG VERPASST — NVDA")
    assert "Nicht hinterherspringen" in text and "⚠️ Markt-Gegenwind" in text

def test_format_update():
    pos = {"ticker": "NVDA", "stop": 109.95, "target1": 111.65, "liste": "spekulativ"}
    assert "Ziel 1 erreicht" in tg.format_update("target1", pos, 111.7)
    assert "nachgezogen" in tg.format_update("trail", pos, 111.7)

def test_send_message_ohne_token_false(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert tg.send_message("hi") is False
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_telegram.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren** — `trainspotter/telegram_bot.py`:

```python
import os
import requests

def _api(method: str) -> str | None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    return f"https://api.telegram.org/bot{token}/{method}" if token else None

def send_message(text: str) -> bool:
    url, chat = _api("sendMessage"), os.environ.get("TELEGRAM_CHAT_ID")
    if not url or not chat:
        return False
    for _ in range(3):
        try:
            r = requests.post(url, json={"chat_id": chat, "text": text}, timeout=15)
            if r.ok:
                return True
        except requests.RequestException:
            pass
    return False

def poll_commands(offset: int) -> tuple[list[str], int]:
    url = _api("getUpdates")
    if not url:
        return [], offset
    try:
        r = requests.get(url, params={"offset": offset, "timeout": 0}, timeout=15)
        updates = r.json().get("result", [])
    except (requests.RequestException, ValueError):
        return [], offset
    cmds = []
    for u in updates:
        offset = max(offset, u["update_id"] + 1)
        text = (u.get("message") or {}).get("text", "")
        if text.startswith("/"):
            cmds.append(text.split()[0])
    return cmds, offset

def format_alert(alert: dict, ki: dict | None) -> str:
    warn = f"\n⚠️ {alert['warning']}" if alert.get("warning") else ""
    if alert["status"] == "missed":
        return (f"🚂💨 ZUG VERPASST — {alert['ticker']} [{alert['liste']}]\n"
                f"Schon {alert['dist_pct']:+.1f}% über Ausbruch {alert['breakout_level']:.2f}. "
                f"Nicht hinterherspringen.{warn}")
    lines = [f"🚂 ZUG ERKANNT — {alert['ticker']} [{alert['liste']}]",
             f"Regeln: {', '.join(alert['reasons'])}",
             f"Ausbruch über {alert['breakout_level']:.2f} | Kurs {alert['price']:.2f} ({alert['dist_pct']:+.1f}%)",
             f"Einstieg: {alert['entry']:.2f} | Stop: {alert['stop']:.2f} | Ziel 1: {alert['target1']:.2f}",
             "Danach: Trailing-Stop."]
    if ki and ki.get("einschaetzung"):
        lines.append(f"KI: {ki['einschaetzung']}")
    return "\n".join(lines) + warn

def format_update(event: str, pos: dict, price: float) -> str:
    t = pos["ticker"]
    if event == "target1":
        return f"🔔 {t}: Ziel 1 erreicht ({pos['target1']:.2f}) — halbe Position verbucht, Rest trailt."
    if event == "trail":
        return f"🔔 {t}: Trailing-Stop nachgezogen auf {pos['stop']:.2f} (Kurs {price:.2f})."
    return f"🔔 {t}: {event} (Kurs {price:.2f})."

def format_trade_closed(trade: dict) -> str:
    emo = "✅" if float(trade["pnl_eur"]) >= 0 else "❌"
    return (f"{emo} {trade['ticker']} geschlossen [{trade['reason']}]: "
            f"{float(trade['pnl_eur']):+.2f} € ({float(trade['pnl_pct']):+.1f}%)")
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_telegram.py -v` — Expected: 4 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Telegram-Bot (Senden, Kommando-Polling, deutsche Formate)"`

---

### Task 11: KI-Bewertung

**Files:**
- Create: `trainspotter/ai_review.py`, `tests/test_ai_review.py`

**Interfaces:**
- Consumes: Trigger-Ergebnis, `data.yahoo.headlines`
- Produces: `review_trigger(alert: dict, headlines: list[str]) -> dict | None` — ruft `claude -p <prompt>` per subprocess (Timeout 180 s, Env `CLAUDE_CODE_OAUTH_TOKEN` kommt aus dem Workflow); erwartet JSON mit `einschaetzung` (2 Sätze, deutsch), `katalysator` (string|null), `risiko` (string), `liste_ok` (bool). Jeder Fehler → `None` (Alert geht dann ohne KI-Zeile raus — KI kann abwerten, nie erfinden, nie blockieren durch Ausfall).

- [ ] **Step 1: Failing Tests** — `tests/test_ai_review.py`:

```python
import subprocess
from trainspotter import ai_review

ALERT = {"ticker": "NVDA", "liste": "spekulativ", "price": 101.5, "breakout_level": 100.0,
         "vol_ratio": 2.5, "reasons": ["r1"], "score": 90}

class FakeProc:
    def __init__(self, out):
        self.stdout, self.returncode = out, 0

def test_parst_json_aus_antwort(monkeypatch):
    out = 'Hier: {"einschaetzung": "Zug faehrt.", "katalysator": "Earnings", "risiko": "Markt", "liste_ok": true}'
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc(out))
    r = ai_review.review_trigger(ALERT, ["News 1"])
    assert r["einschaetzung"] == "Zug faehrt." and r["liste_ok"] is True

def test_none_bei_muell(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc("kein json"))
    assert ai_review.review_trigger(ALERT, []) is None

def test_none_bei_timeout(monkeypatch):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired("claude", 180)
    monkeypatch.setattr(subprocess, "run", boom)
    assert ai_review.review_trigger(ALERT, []) is None
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_ai_review.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren** — `trainspotter/ai_review.py`:

```python
import json, re, subprocess

PROMPT = """Du bist nüchterner Trading-Analyst. Ein regelbasierter Momentum-Scanner hat einen Ausbruch erkannt:
Ticker: {ticker} | Liste: {liste} | Kurs: {price} | Ausbruchsniveau: {level}
Volumen: {vol}x zeitanteiliger Schnitt | Regel-Score: {score} | Regeln: {reasons}
Aktuelle Schlagzeilen: {headlines}

Bewerte NUR auf Basis dieser Daten. Antworte AUSSCHLIESSLICH mit einem JSON-Objekt:
{{"einschaetzung": "<max 2 Saetze deutsch>", "katalysator": "<string oder null>",
"risiko": "<1 Satz>", "liste_ok": <true/false>}}"""

def review_trigger(alert: dict, headlines: list[str]) -> dict | None:
    prompt = PROMPT.format(ticker=alert["ticker"], liste=alert["liste"], price=alert["price"],
                           level=alert["breakout_level"], vol=alert["vol_ratio"],
                           score=alert["score"], reasons=", ".join(alert["reasons"]),
                           headlines="; ".join(headlines) or "keine")
    try:
        r = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=180)
        m = re.search(r"\{.*\}", r.stdout, re.S)
        d = json.loads(m.group(0))
        return d if "einschaetzung" in d else None
    except Exception:
        return None    # KI-Ausfall darf nie einen Alert verhindern
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_ai_review.py -v` — Expected: 3 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: KI-Bewertung via Claude Code CLI mit strikter Degradation"`

---

### Task 12: Statistik & Reports

**Files:**
- Create: `trainspotter/reports.py`, `tests/test_reports.py`

**Interfaces:**
- Consumes: `state.load_trades`, Watchlist-Einträge, Positions-Dicts
- Produces: `compute_stats(trades: list[dict]) -> dict` (`{liste: {"n","hit_rate","avg_win","avg_loss","profit_factor","total_eur"}}`), `format_depesche(watchlist: list[dict]) -> str` (Heartbeat: auch bei leerer Liste Text), `format_bilanz(stats, open_positions, today_trades) -> str` (endet immer mit `cfg.DISCLAIMER`), `format_stats_command(stats) -> str`, `format_status_command(open_positions, today_alert_ids) -> str`

- [ ] **Step 1: Failing Tests** — `tests/test_reports.py`:

```python
import pytest
import trainspotter.config as cfg
from trainspotter import reports

TRADES = [{"liste": "konservativ", "pnl_eur": "50.0"},
          {"liste": "konservativ", "pnl_eur": "-20.0"},
          {"liste": "konservativ", "pnl_eur": "30.0"}]

def test_compute_stats():
    s = reports.compute_stats(TRADES)["konservativ"]
    assert s["n"] == 3
    assert s["hit_rate"] == pytest.approx(66.7, abs=0.1)
    assert s["profit_factor"] == pytest.approx(4.0)      # 80 Gewinn / 20 Verlust
    assert s["total_eur"] == pytest.approx(60.0)

def test_depesche_heartbeat_leer():
    assert "keine Kandidaten" in reports.format_depesche([])

def test_depesche_mit_eintraegen():
    wl = [{"ticker": "NVDA", "liste": "spekulativ", "breakout_level": 100.0, "score": 90, "market": "us"}]
    d = reports.format_depesche(wl)
    assert "NVDA" in d and "100.00" in d and "1 Züge" in d

def test_bilanz_hat_disclaimer():
    assert cfg.DISCLAIMER in reports.format_bilanz(reports.compute_stats(TRADES), [], [])
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_reports.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren** — `trainspotter/reports.py`:

```python
import trainspotter.config as cfg

def compute_stats(trades: list[dict]) -> dict:
    out = {}
    for liste in cfg.LISTEN:
        pnls = [float(t["pnl_eur"]) for t in trades if t["liste"] == liste]
        wins = [p for p in pnls if p >= 0]
        losses = [p for p in pnls if p < 0]
        out[liste] = {"n": len(pnls),
                      "hit_rate": round(len(wins) / len(pnls) * 100, 1) if pnls else 0.0,
                      "avg_win": round(sum(wins) / len(wins), 2) if wins else 0.0,
                      "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0.0,
                      "profit_factor": round(sum(wins) / abs(sum(losses)), 2) if losses else 0.0,
                      "total_eur": round(sum(pnls), 2)}
    return out

def format_depesche(watchlist: list[dict]) -> str:
    if not watchlist:
        return "📋 Morgen-Depesche: heute keine Kandidaten am Bahnsteig. (System läuft.)"
    lines = [f"📋 Morgen-Depesche — {len(watchlist)} Züge am Bahnsteig:"]
    for e in watchlist:
        lines.append(f"{e['ticker']} [{e['liste'][:4]}|{e['market']}] "
                     f"Ausbruch {e['breakout_level']:.2f} (Score {e['score']})")
    return "\n".join(lines)

def _stats_lines(stats: dict) -> list[str]:
    return [f"{l}: {s['n']} Trades, Treffer {s['hit_rate']}%, "
            f"PF {s['profit_factor']}, Summe {s['total_eur']:+.2f} €"
            for l, s in stats.items()]

def format_bilanz(stats: dict, open_positions: list[dict], today_trades: list[dict]) -> str:
    lines = ["📊 Abend-Bilanz"]
    day = sum(float(t["pnl_eur"]) for t in today_trades)
    lines.append(f"Heute geschlossen: {len(today_trades)} Trades, {day:+.2f} €")
    lines += [f"Offen: {p['ticker']} [{p['liste'][:4]}] Stop {p['stop']:.2f}"
              for p in open_positions] or ["Offen: keine Positionen"]
    lines += ["Gesamt:"] + _stats_lines(stats) + [cfg.DISCLAIMER]
    return "\n".join(lines)

def format_stats_command(stats: dict) -> str:
    return "\n".join(["📊 Gesamtstatistik:"] + _stats_lines(stats))

def format_status_command(open_positions: list[dict], today_alert_ids: list[str]) -> str:
    lines = [f"Offen: {p['ticker']} Einstieg {p['entry']:.2f} Stop {p['stop']:.2f}"
             for p in open_positions] or ["Keine offenen Positionen."]
    lines.append(f"Alerts heute: {', '.join(today_alert_ids) or 'keine'}")
    return "\n".join(lines)
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_reports.py -v` — Expected: 4 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Statistik und Report-Formate (Depesche, Bilanz, Kommandos)"`

---

### Task 13: Live-Beobachter

**Files:**
- Create: `trainspotter/live_observer.py`, `scripts/run_observer.py`, `tests/test_observer.py`

**Interfaces:**
- Consumes: alles aus Tasks 3–12
- Produces: `Deps`-Dataclass (`quotes_fn(tickers)->dict`, `index_fn()->float`, `send_fn(text)->bool`, `review_fn(alert)->dict|None`, `now_fn()->datetime`), `load_context(market) -> dict` (`{"market","watchlist","positions","alerts_sent","today"}` aus `state/`-Dateien), `run_cycle(ctx: dict, deps: Deps, session_close: bool = False) -> list[str]` (ein kompletter Durchlauf; mutiert ctx), `persist(ctx)`, `run_session(market: str, max_minutes: int)` (Schleife bis Handelsschluss oder max_minutes; committet bei Events), `build_deps(market) -> Deps` (US: Finnhub-Preise + Yahoo-Volumen-Cache, Refresh alle `US_VOLUME_REFRESH_CYCLES` Zyklen; EU: Yahoo-Intraday)
- State-Dateien: `state/watchlist.json` (Liste), `state/positions_{market}.json`, `state/alerts_sent.json` (`{"YYYY-MM-DD": [ids]}` nur heute+gestern behalten), `state/telegram_offset.json`, `state/history/trades_{market}.csv`

- [ ] **Step 1: Failing Tests** — `tests/test_observer.py`:

```python
from datetime import datetime, timezone
from trainspotter import live_observer as obs

ENTRY = {"ticker": "TTT", "market": "us", "liste": "spekulativ", "score": 90,
         "breakout_level": 100.0, "adr_pct": 4.0, "avg_volume": 1_000_000,
         "criteria": ["volumen_aufbau:2.0x"]}

# 16:00 UTC = 2,5h von 6,5h US-Sitzung -> elapsed 0.385; 900k Volumen -> Ratio 2.34 >= 2.0
def _deps(price, vol=900_000):
    sent = []
    return obs.Deps(quotes_fn=lambda ts: {"TTT": {"price": price, "day_volume": vol}},
                    index_fn=lambda: -0.5, send_fn=lambda t: sent.append(t) or True,
                    review_fn=lambda a: None,
                    now_fn=lambda: datetime(2026, 7, 8, 16, 0, tzinfo=timezone.utc)), sent

def _ctx(tmp_path):
    return {"market": "us", "watchlist": [ENTRY], "positions": [],
            "alerts_sent": {"2026-07-08": []}, "today": "2026-07-08",
            "trades_path": str(tmp_path / "trades.csv")}

def test_zyklus_erzeugt_alert_und_position(tmp_path):
    deps, sent = _deps(101.5)
    ctx = _ctx(tmp_path)
    events = obs.run_cycle(ctx, deps)
    assert any("ZUG ERKANNT" in m for m in sent)
    assert len(ctx["positions"]) == 1
    assert "TTT-2026-07-08" in ctx["alerts_sent"]["2026-07-08"]
    assert events

def test_kein_doppelalert_im_naechsten_zyklus(tmp_path):
    deps, sent = _deps(101.5)
    ctx = _ctx(tmp_path)
    obs.run_cycle(ctx, deps)
    n = len(sent)
    obs.run_cycle(ctx, deps)
    assert len(ctx["positions"]) == 1           # nicht doppelt eroeffnet
    assert len([m for m in sent[n:] if "ZUG ERKANNT" in m]) == 0

def test_stop_schliesst_position_und_meldet(tmp_path):
    deps, sent = _deps(101.5)
    ctx = _ctx(tmp_path)
    obs.run_cycle(ctx, deps)
    deps2, sent2 = _deps(90.0)
    events = obs.run_cycle(ctx, deps2)
    assert ctx["positions"] == []
    assert any("geschlossen" in m for m in sent2)

def test_movers_entries_erzeugt_adhoc_eintraege():
    import pandas as pd
    close = pd.Series([100 + 0.3 * i for i in range(80)])
    df = pd.DataFrame({"Open": close - 0.1, "High": close + 1, "Low": close - 1,
                       "Close": close, "Volume": [1_000_000] * 80})
    entries = obs.movers_entries(["MOV"], lambda ts: {"MOV": df}, "us",
                                 known={"TTT"})
    assert entries[0]["ticker"] == "MOV" and entries[0]["criteria"] == ["tages_topmover"]
    assert obs.movers_entries(["TTT"], lambda ts: {}, "us", known={"TTT"}) == []
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_observer.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren**

`trainspotter/live_observer.py`:
```python
import os, time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
import trainspotter.config as cfg
from trainspotter import calendar_utils as cal, paper_trading as pt, reports, state, telegram_bot as tg, triggers
from trainspotter.data import yahoo

@dataclass
class Deps:
    quotes_fn: Callable
    index_fn: Callable
    send_fn: Callable
    review_fn: Callable
    now_fn: Callable

STATE = {"watchlist": "state/watchlist.json", "alerts": "state/alerts_sent.json",
         "offset": "state/telegram_offset.json"}

def load_context(market: str) -> dict:
    today = datetime.now(timezone.utc).astimezone(cal.TZ[market]).date().isoformat()
    wl = [e for e in state.load_json(STATE["watchlist"], []) if e["market"] == market]
    alerts = state.load_json(STATE["alerts"], {})
    alerts = dict(sorted(alerts.items())[-2:])            # nur gestern+heute behalten
    alerts.setdefault(today, [])
    return {"market": market, "watchlist": wl, "today": today, "alerts_sent": alerts,
            "positions": state.load_json(f"state/positions_{market}.json", [])}

def movers_entries(tickers: list[str], fetch_fn, market: str, known: set[str]) -> list[dict]:
    """Tages-Topmover, die nicht auf der Watchlist stehen: Ad-hoc-Bahnsteig-Eintrag
    mit Ausbruchsniveau aus der Tageshistorie (Spec 6.2, zweite Quelle)."""
    from trainspotter import indicators as ind
    fresh = [t for t in tickers if t not in known]
    if not fresh:
        return []
    out = []
    for t, df in fetch_fn(fresh).items():
        try:
            if len(df) < 60:
                continue
            adr = ind.adr_pct(df["High"], df["Low"], df["Close"])
            if adr < cfg.ADR_MIN_KONS:
                continue
            out.append({"ticker": t, "market": market,
                        "liste": "spekulativ" if adr >= cfg.ADR_MIN_SPEC else "konservativ",
                        "score": cfg.SCORE_MIN, "breakout_level": ind.breakout_level(df["High"]),
                        "adr_pct": round(adr, 2),
                        "avg_volume": float(df["Volume"].iloc[-20:].mean()),
                        "criteria": ["tages_topmover"]})
        except Exception:
            continue
    return out

def persist(ctx: dict):
    state.save_json(f"state/positions_{ctx['market']}.json", ctx["positions"])
    state.save_json(STATE["alerts"], ctx["alerts_sent"])

def run_cycle(ctx: dict, deps: Deps, session_close: bool = False) -> list[str]:
    now = deps.now_fn()
    tickers = [e["ticker"] for e in ctx["watchlist"]] + [p["ticker"] for p in ctx["positions"]]
    quotes = deps.quotes_fn(sorted(set(tickers)))
    index_chg = deps.index_fn()
    elapsed = cal.elapsed_fraction(now, ctx["market"])
    events: list[str] = []
    sent_today = set(ctx["alerts_sent"][ctx["today"]])
    open_ids = {p["id"] for p in ctx["positions"]}
    cands = []
    for e in ctx["watchlist"]:
        q = quotes.get(e["ticker"])
        if not q:
            continue
        try:
            r = triggers.check_trigger(e, q["price"], q["day_volume"], index_chg, elapsed, ctx["today"])
            if r and r["id"] not in open_ids:
                cands.append(r)
        except Exception:
            continue                                     # kranker Ticker stoppt nie den Scan
    for alert in triggers.apply_alert_discipline(cands, sent_today, _sent_counts(ctx)):
        ki = deps.review_fn(alert)
        deps.send_fn(tg.format_alert(alert, ki))
        ctx["alerts_sent"][ctx["today"]].append(alert["id"])
        if alert["status"] == "alert":
            ctx["positions"].append(pt.open_position(alert, now.isoformat()))
            events.append(f"alert:{alert['id']}")
    still_open = []
    trades_path = ctx.get("trades_path") or f"state/history/trades_{ctx['market']}.csv"
    for pos in ctx["positions"]:
        q = quotes.get(pos["ticker"])
        if not q:
            still_open.append(pos)
            continue
        evs, trade = pt.update_position(pos, q["price"], now.isoformat(), session_close)
        for ev in evs:
            if ev in ("target1", "trail"):
                deps.send_fn(tg.format_update(ev, pos, q["price"]))
        if trade:
            state.append_trade(trades_path, trade)
            deps.send_fn(tg.format_trade_closed(trade))
            events.append(f"closed:{trade['id']}")
        else:
            still_open.append(pos)
        events += evs
    ctx["positions"] = still_open
    return events

def _sent_counts(ctx: dict) -> dict:
    """Wie viele Alerts je Liste heute schon raus sind (Ticker -> Liste aus der Watchlist)."""
    liste_by_ticker = {e["ticker"]: e["liste"] for e in ctx["watchlist"]}
    counts = {l: 0 for l in cfg.LISTEN}
    for alert_id in ctx["alerts_sent"][ctx["today"]]:
        ticker = alert_id.rsplit("-", 3)[0]               # "NVDA-2026-07-08" -> "NVDA"
        counts[liste_by_ticker.get(ticker, "spekulativ")] += 1
    return counts

def _handle_commands(ctx: dict):
    off = state.load_json(STATE["offset"], {"offset": 0})
    cmds, new_off = tg.poll_commands(off["offset"])
    for c in cmds:
        if c == "/status":
            tg.send_message(reports.format_status_command(ctx["positions"],
                                                          ctx["alerts_sent"][ctx["today"]]))
        elif c == "/stats":
            trades = state.load_trades("state/history/trades_us.csv") + \
                     state.load_trades("state/history/trades_eu.csv")
            tg.send_message(reports.format_stats_command(reports.compute_stats(trades)))
    if new_off != off["offset"]:
        state.save_json(STATE["offset"], {"offset": new_off})

def build_deps(market: str) -> Deps:
    if market == "eu":
        return Deps(quotes_fn=yahoo.intraday_snapshot,
                    index_fn=lambda: yahoo.index_change_pct("eu"),
                    send_fn=tg.send_message, review_fn=_review,
                    now_fn=lambda: datetime.now(timezone.utc))
    from trainspotter.data.finnhub import Finnhub
    fh = Finnhub(os.environ.get("FINNHUB_API_KEY", ""))
    cache: dict = {"cycle": 0, "vol": {}}

    def us_quotes(tickers):
        if cache["cycle"] % cfg.US_VOLUME_REFRESH_CYCLES == 0:
            cache["vol"] = yahoo.intraday_snapshot(tickers)   # Volumen ~15 Min verzoegert
        cache["cycle"] += 1
        out = {}
        for t in tickers:
            q = fh.quote(t)                                   # Preis in Echtzeit
            vol = cache["vol"].get(t, {}).get("day_volume", 0.0)
            if q:
                out[t] = {"price": q["price"], "day_volume": vol}
        return out

    return Deps(quotes_fn=us_quotes, index_fn=lambda: yahoo.index_change_pct("us"),
                send_fn=tg.send_message, review_fn=_review,
                now_fn=lambda: datetime.now(timezone.utc))

def _review(alert):
    from trainspotter import ai_review
    return ai_review.review_trigger(alert, yahoo.headlines(alert["ticker"]))

def run_session(market: str, max_minutes: int):
    now = datetime.now(timezone.utc)
    local_date = now.astimezone(cal.TZ[market]).date()
    if not cal.is_trading_day(local_date, market):
        return
    open_t, close_t = cal.session_bounds(local_date, market)
    hard_end = now + timedelta(minutes=max_minutes)
    ctx, deps = load_context(market), build_deps(market)
    data_fail, cycle_no = 0, 0
    while datetime.now(timezone.utc) < min(close_t, hard_end):
        if datetime.now(timezone.utc) < open_t:
            time.sleep(30)
            continue
        if market == "us" and cycle_no % 10 == 0:         # Spec 6.2: Topmover als 2. Quelle
            known = {e["ticker"] for e in ctx["watchlist"]}
            ctx["watchlist"] += movers_entries(yahoo.top_movers_us(), yahoo.daily_history,
                                               "us", known)
        cycle_no += 1
        try:
            events = run_cycle(ctx, deps)
            data_fail = 0
        except Exception:
            events, data_fail = [], data_fail + 1
            if data_fail == 5:
                tg.send_message("⚠️ Scanner fährt blind — Datenquelle antwortet nicht.")
        if cal.should_poll_commands(datetime.now(timezone.utc), market):
            _handle_commands(ctx)
        if events:
            persist(ctx)
            state.commit_and_push(["state"], f"state: {market} {len(events)} Ereignisse")
        time.sleep(cfg.CYCLE_SECONDS)
    if datetime.now(timezone.utc) >= close_t:                 # regulaerer Schluss
        run_cycle(ctx, deps, session_close=True)
    persist(ctx)
    state.commit_and_push(["state"], f"state: {market} Sitzungsende")
```

`scripts/run_observer.py`:
```python
import argparse
from trainspotter.live_observer import run_session

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--market", choices=["us", "eu"], required=True)
    p.add_argument("--max-minutes", type=int, default=335)
    a = p.parse_args()
    run_session(a.market, a.max_minutes)
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_observer.py -v` — Expected: 4 passed. Danach Gesamtlauf: `.venv/bin/pytest -q` — Expected: alles grün.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Live-Beobachter mit Sitzungsschleife und injizierbaren Abhaengigkeiten"`

---

### Task 14: Tages-Skripte (Nacht-Scan, Depesche, Bilanz, Testnachricht)

**Files:**
- Create: `scripts/run_night_scan.py`, `scripts/send_depesche.py`, `scripts/send_bilanz.py`, `scripts/send_test_message.py`, `tests/test_scripts.py`

**Interfaces:**
- Consumes: `universe`, `data.yahoo.daily_history`, `night_scan`, `reports`, `state`, `telegram_bot`
- Produces: `run_night_scan.build(us_universe, de_universe, fetch_fn, index_fetch_fn) -> list[dict]` (testbare Kernfunktion; Skript-`main()` verdrahtet echte Quellen und schreibt `state/watchlist.json` + committet)

- [ ] **Step 1: Failing Test** — `tests/test_scripts.py`:

```python
import pandas as pd
import importlib
run_night_scan = importlib.import_module("scripts.run_night_scan")

def _df(n=80):
    close = pd.Series([100 + 0.3 * i for i in range(n)])
    return pd.DataFrame({"Open": close - 0.1, "High": close + 1, "Low": close - 1,
                         "Close": close, "Volume": [1_000_000] * (n - 5) + [2_000_000] * 5})

def test_build_findet_kandidaten_und_markiert_markt():
    data = {"TTT": _df()}
    wl = run_night_scan.build(["TTT"], ["SAP.DE"],
                              fetch_fn=lambda ts: {t: _df() for t in ts if t == "TTT"},
                              index_fetch_fn=lambda m: pd.Series([100.0] * 80))
    assert len(wl) == 1 and wl[0]["ticker"] == "TTT" and wl[0]["market"] == "us"
```

Dazu `scripts/__init__.py` (leer) anlegen, damit der Import funktioniert.

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_scripts.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren**

`scripts/run_night_scan.py`:
```python
import pandas as pd
from trainspotter import night_scan, state, universe
from trainspotter.data import yahoo
import trainspotter.config as cfg

def build(us_universe, de_universe, fetch_fn, index_fetch_fn) -> list[dict]:
    entries = []
    for market, tickers in (("us", us_universe), ("eu", de_universe)):
        index_close = index_fetch_fn(market)
        data = fetch_fn(tickers)
        for t, df in data.items():
            try:
                e = night_scan.platform_score(t, df, index_close, market)
                if e:
                    entries.append(e)
            except Exception:
                continue
    return night_scan.build_watchlist(entries)

def _index_close(market: str) -> pd.Series:
    h = yahoo.daily_history([cfg.INDEX_SYMBOL[market]], period="2y")
    df = h.get(cfg.INDEX_SYMBOL[market])
    return df["Close"] if df is not None else pd.Series(dtype=float)

def main():
    wl = build(universe.load_us_universe(), universe.load_de_universe(),
               fetch_fn=yahoo.daily_history, index_fetch_fn=_index_close)
    state.save_json("state/watchlist.json", wl)
    state.commit_and_push(["state/watchlist.json"], f"state: Watchlist {len(wl)} Titel")

if __name__ == "__main__":
    main()
```

`scripts/send_depesche.py`:
```python
from trainspotter import reports, state, telegram_bot as tg

if __name__ == "__main__":
    wl = state.load_json("state/watchlist.json", [])
    tg.send_message(reports.format_depesche(wl))     # Heartbeat: sendet auch bei leer
```

`scripts/send_bilanz.py`:
```python
from datetime import date
from trainspotter import reports, state, telegram_bot as tg

if __name__ == "__main__":
    trades = state.load_trades("state/history/trades_us.csv") + \
             state.load_trades("state/history/trades_eu.csv")
    today = date.today().isoformat()
    today_trades = [t for t in trades if t["closed"].startswith(today)]
    open_pos = state.load_json("state/positions_us.json", []) + \
               state.load_json("state/positions_eu.json", [])
    tg.send_message(reports.format_bilanz(reports.compute_stats(trades), open_pos, today_trades))
```

`scripts/send_test_message.py`:
```python
from trainspotter import telegram_bot as tg

if __name__ == "__main__":
    ok = tg.send_message("🚂 TrainSpotter Testnachricht — Verbindung steht.")
    print("OK" if ok else "FEHLER: Token/Chat-ID pruefen")
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_scripts.py -v` — Expected: 1 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Tagesskripte Nacht-Scan, Depesche, Bilanz, Testnachricht"`

---

### Task 15: Backtest

**Files:**
- Create: `trainspotter/backtest.py`, `scripts/run_backtest.py`, `tests/test_backtest.py`

**Interfaces:**
- Consumes: `night_scan.platform_score`, `cfg.*`
- Produces: `simulate_trade(entry: dict, df: pd.DataFrame, day_idx: int) -> dict | None` (simuliert einen Trade ab Tag `day_idx` auf OHLC-Tagesbasis) und `simulate(daily: dict[str, pd.DataFrame], index_close: pd.Series, market: str, start_idx: int = 60) -> pd.DataFrame` (für jeden Tag Watchlist bauen, am Folgetag Ausbruch prüfen, Trade simulieren; Spalten = `ticker, day, liste, entry, exit, pnl_pct, reason`)
- Trade-Simulation: Einstieg wenn `High > level` und `Open < level × 1,04` (nicht drüber gegappt); Einstiegskurs `max(level, Open) × 1,002`; dann je Tag: `Low ≤ stop` → Ausstieg zum Stop; `High ≥ target1` → halbe Position zu Ziel 1; Rest: spekulativ zum Tagesschluss, konservativ zum Schluss von Tag +3. Konservative Annahme: wenn Stop und Ziel am selben Tag erreichbar wären, zählt der **Stop** (pessimistisch).

- [ ] **Step 1: Failing Tests** — `tests/test_backtest.py`:

```python
import pandas as pd
import pytest
from trainspotter import backtest

ENTRY = {"ticker": "TTT", "market": "us", "liste": "konservativ", "score": 90,
         "breakout_level": 100.0, "adr_pct": 2.0, "avg_volume": 1_000_000, "criteria": []}

def _day(o, h, l, c):
    return {"Open": o, "High": h, "Low": l, "Close": c, "Volume": 1_000_000}

def test_stop_am_ersten_tag():
    df = pd.DataFrame([_day(99, 101, 96, 97)])           # bricht aus, faellt auf Stop 97.0
    t = backtest.simulate_trade(ENTRY, df, 0)
    assert t["reason"] == "stop"
    # Einstieg max(100, 99)*1.002 = 100.2; Stop 100*0.97 = 97 -> -3.19%
    assert t["pnl_pct"] == pytest.approx((97.0 / 100.2 - 1) * 100, abs=0.01)

def test_ziel1_und_zeitausstieg():
    df = pd.DataFrame([_day(99, 106, 99, 105),           # Einstieg 100.2, Ziel1 104.208 erreicht
                       _day(105, 107, 104, 106),
                       _day(106, 108, 105, 107)])        # Zeitausstieg Tag 3 zu 107
    t = backtest.simulate_trade(ENTRY, df, 0)
    assert t["reason"] == "zeitausstieg"
    halb_ziel = (104.208 / 100.2 - 1) * 100 / 2
    halb_rest = (107.0 / 100.2 - 1) * 100 / 2
    assert t["pnl_pct"] == pytest.approx(halb_ziel + halb_rest, abs=0.05)

def test_gap_drueber_kein_trade():
    df = pd.DataFrame([_day(105, 106, 104, 105)])        # Open 5% ueber Level -> kein Einstieg
    assert backtest.simulate_trade(ENTRY, df, 0) is None
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_backtest.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren**

`trainspotter/backtest.py`:
```python
import pandas as pd
import trainspotter.config as cfg
from trainspotter import night_scan

def simulate_trade(entry: dict, df: pd.DataFrame, day_idx: int) -> dict | None:
    level, liste = entry["breakout_level"], entry["liste"]
    d0 = df.iloc[day_idx]
    if d0["High"] <= level or d0["Open"] >= level * 1.04:
        return None
    buy = max(level, float(d0["Open"])) * (1 + cfg.SLIPPAGE_PCT / 100)
    stop = level * (1 - cfg.STOP_PCT[liste] / 100)
    target1 = buy * (1 + cfg.TARGET1_PCT[liste] / 100)
    horizon = 1 if liste == "spekulativ" else cfg.MAX_HOLD_DAYS_KONS
    half_done, pnl_pct = False, 0.0
    last = min(day_idx + horizon, len(df)) - 1
    for i in range(day_idx, last + 1):
        d = df.iloc[i]
        if d["Low"] <= stop:                              # pessimistisch: Stop vor Ziel
            frac = 0.5 if half_done else 1.0
            return _result(entry, i, buy, stop, pnl_pct + frac * (stop / buy - 1) * 100,
                           "trail_stop" if half_done else "stop")
        if not half_done and d["High"] >= target1:
            pnl_pct += 0.5 * (target1 / buy - 1) * 100
            half_done, stop = True, buy                   # Rest: Breakeven-Stop (Tagesbasis)
    exit_price = float(df.iloc[last]["Close"])
    frac = 0.5 if half_done else 1.0
    reason = "tagesschluss" if liste == "spekulativ" else "zeitausstieg"
    return _result(entry, last, buy, exit_price, pnl_pct + frac * (exit_price / buy - 1) * 100, reason)

def _result(entry, day, buy, exit_price, pnl_pct, reason):
    return {"ticker": entry["ticker"], "day": int(day), "liste": entry["liste"],
            "entry": round(buy, 4), "exit": round(float(exit_price), 4),
            "pnl_pct": round(pnl_pct, 3), "reason": reason}

def simulate(daily: dict[str, pd.DataFrame], index_close: pd.Series,
             market: str, start_idx: int = 60) -> pd.DataFrame:
    trades = []
    n = len(index_close)
    for t in range(start_idx, n - 1):
        for ticker, df in daily.items():
            if len(df) <= t + 1:
                continue
            try:
                e = night_scan.platform_score(ticker, df.iloc[:t + 1], index_close.iloc[:t + 1], market)
                if e:
                    tr = simulate_trade(e, df, t + 1)
                    if tr:
                        trades.append(tr)
            except Exception:
                continue
    return pd.DataFrame(trades)
```

`scripts/run_backtest.py`:
```python
"""Tages-Backtest: python scripts/run_backtest.py --market eu [--years 3]"""
import argparse
import trainspotter.config as cfg
from trainspotter import backtest, reports, universe
from trainspotter.data import yahoo

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--market", choices=["us", "eu"], default="eu")
    p.add_argument("--years", type=int, default=3)
    a = p.parse_args()
    tickers = universe.load_de_universe() if a.market == "eu" else universe.load_us_universe()[:500]
    daily = yahoo.daily_history(tickers, period=f"{a.years}y")
    idx = yahoo.daily_history([cfg.INDEX_SYMBOL[a.market]], period=f"{a.years}y")
    index_close = idx[cfg.INDEX_SYMBOL[a.market]]["Close"]
    df = backtest.simulate(daily, index_close, a.market)
    if df.empty:
        print("Keine Trades gefunden.")
    else:
        print(df.groupby("liste")["pnl_pct"].describe())
        wins = df[df.pnl_pct > 0]
        print(f"\nTrades: {len(df)} | Trefferquote: {len(wins) / len(df) * 100:.1f}% "
              f"| Ø PnL: {df.pnl_pct.mean():.2f}%")
        df.to_csv("state/history/backtest_result.csv", index=False)
```

Hinweis US-Backtest: volle 7000 Titel × 750 Tage dauert Stunden — deshalb kappt das Skript US auf 500 Titel; für die Regelvalidierung reicht das. Steht so in der README.

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_backtest.py -v` — Expected: 3 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Tages-Backtest fuer Regelvalidierung"`

---

### Task 16: Trockenlauf (Dry-Run)

**Files:**
- Create: `scripts/run_dry_run.py`, `tests/fixtures/recorded_day.json`, `tests/test_dry_run.py`

**Interfaces:**
- Consumes: `live_observer.run_cycle`, `Deps`
- Produces: `run(fixture_path: str) -> dict` (`{"alerts": int, "closed": int, "open_end": int}`) — spielt aufgezeichnete Zyklen ohne Netz/Git durch (`TRAINSPOTTER_NO_GIT=1` setzt das Skript selbst); letzter Zyklus mit `session_close=True`.

- [ ] **Step 1: Fixture + Failing Test**

`tests/fixtures/recorded_day.json`:
```json
{"watchlist": [{"ticker": "TTT", "market": "us", "liste": "spekulativ", "score": 90,
                "breakout_level": 100.0, "adr_pct": 4.0, "avg_volume": 1000000,
                "criteria": ["volumen_aufbau:2.0x"]}],
 "today": "2026-07-08",
 "cycles": [
   {"time": "2026-07-08T14:00:00+00:00", "index": 0.2, "quotes": {"TTT": {"price": 99.0, "day_volume": 100000}}},
   {"time": "2026-07-08T15:00:00+00:00", "index": 0.3, "quotes": {"TTT": {"price": 101.5, "day_volume": 900000}}},
   {"time": "2026-07-08T18:00:00+00:00", "index": 0.4, "quotes": {"TTT": {"price": 108.0, "day_volume": 2000000}}},
   {"time": "2026-07-08T19:55:00+00:00", "index": 0.4, "quotes": {"TTT": {"price": 107.0, "day_volume": 2500000}}}
 ]}
```

`tests/test_dry_run.py`:
```python
import importlib
dry = importlib.import_module("scripts.run_dry_run")

def test_trockenlauf_kompletter_tag():
    r = dry.run("tests/fixtures/recorded_day.json")
    assert r["alerts"] == 1        # Zyklus 2 loest aus (Ausbruch + Volumen)
    assert r["open_end"] == 0      # spekulativ -> zum Schluss zwangsgeschlossen
    assert r["closed"] >= 1
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_dry_run.py -v` — Expected: FAIL.
- [ ] **Step 3: Implementieren** — `scripts/run_dry_run.py`:

```python
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
```

Geschlossene Trades landen dank `trades_path` in einem Temp-Verzeichnis — der Trockenlauf hinterlässt nichts im Repo.

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_dry_run.py -v && .venv/bin/pytest -q` — Expected: alles grün, `git status` zeigt keine liegengebliebene trades-CSV.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Trockenlauf-Modus mit aufgezeichnetem Handelstag"`

---

### Task 17: GitHub-Actions-Workflows

**Files:**
- Create: `.github/workflows/tests.yml`, `night-scan.yml`, `depesche.yml`, `observer-eu.yml`, `observer-us.yml`, `bilanz.yml`, `tests/test_workflows.py`

**Interfaces:**
- Consumes: alle Skripte aus Tasks 13–14; Repo-Secrets `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `FINNHUB_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`
- Cron-Zeiten in UTC, ausgelegt auf Sommerzeit (MESZ = UTC+2). Winterhalbjahr: Läufe starten relativ zur Börse bis zu 1 h früher (unschädlich, Skript wartet auf Öffnung) — dokumentiert in README.

- [ ] **Step 1: Failing Test** — `tests/test_workflows.py`:

```python
import glob, yaml

def test_alle_workflows_valides_yaml_mit_jobs():
    files = glob.glob(".github/workflows/*.yml")
    assert len(files) == 6
    for f in files:
        d = yaml.safe_load(open(f))
        assert "jobs" in d, f
```

- [ ] **Step 2: Fehlschlag verifizieren** — Run: `.venv/bin/pytest tests/test_workflows.py -v` — Expected: FAIL (0 Dateien).
- [ ] **Step 3: Workflows anlegen**

Gemeinsame Env-Definition (in jedem Workflow-Job außer tests.yml identisch einsetzen):
```yaml
    env:
      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
```

`.github/workflows/tests.yml`:
```yaml
name: tests
on: [push, pull_request]
jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -r requirements.txt
      - run: pytest -q
        env: {TRAINSPOTTER_NO_GIT: '1'}
```

`.github/workflows/night-scan.yml`:
```yaml
name: night-scan
on:
  schedule:
    - cron: '0 5 * * 1-5'      # 07:00 MESZ
  workflow_dispatch: {}
permissions: {contents: write}
concurrency: {group: night-scan, cancel-in-progress: false}
jobs:
  scan:
    runs-on: ubuntu-latest
    timeout-minutes: 120
    env:
      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -r requirements.txt
      - run: |
          git config user.name "trainspotter-bot"
          git config user.email "bot@users.noreply.github.com"
      - run: python scripts/run_night_scan.py
```

`.github/workflows/depesche.yml`:
```yaml
name: depesche
on:
  schedule:
    - cron: '45 6 * * 1-5'     # 08:45 MESZ, Heartbeat
  workflow_dispatch: {}
jobs:
  send:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env:
      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -r requirements.txt
      - run: python scripts/send_depesche.py
```

`.github/workflows/observer-eu.yml` (Sitzung 09:00–17:30 MESZ = 07:00–15:30 UTC; zwei Läufe decken sie ab, `concurrency` verhindert Parallelität):
```yaml
name: observer-eu
on:
  schedule:
    - cron: '55 6 * * 1-5'     # Teil 1: ab 08:55 MESZ, max 335 Min
    - cron: '25 12 * * 1-5'    # Teil 2: wartet via concurrency, laeuft bis Schluss
  workflow_dispatch: {}
permissions: {contents: write}
concurrency: {group: observer-eu, cancel-in-progress: false}
jobs:
  observe:
    runs-on: ubuntu-latest
    timeout-minutes: 350
    env:
      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
      FINNHUB_API_KEY: ${{ secrets.FINNHUB_API_KEY }}
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -r requirements.txt
      - run: npm install -g @anthropic-ai/claude-code
      - run: |
          git config user.name "trainspotter-bot"
          git config user.email "bot@users.noreply.github.com"
      - run: python scripts/run_observer.py --market eu --max-minutes 335
```

`.github/workflows/observer-us.yml`:
```yaml
name: observer-us
on:
  schedule:
    - cron: '20 13 * * 1-5'    # Teil 1: ab 15:20 MESZ
    - cron: '50 18 * * 1-5'    # Teil 2: bis US-Schluss 22:00 MESZ
  workflow_dispatch: {}
permissions: {contents: write}
concurrency: {group: observer-us, cancel-in-progress: false}
jobs:
  observe:
    runs-on: ubuntu-latest
    timeout-minutes: 350
    env:
      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
      FINNHUB_API_KEY: ${{ secrets.FINNHUB_API_KEY }}
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -r requirements.txt
      - run: npm install -g @anthropic-ai/claude-code
      - run: |
          git config user.name "trainspotter-bot"
          git config user.email "bot@users.noreply.github.com"
      - run: python scripts/run_observer.py --market us --max-minutes 335
```

`.github/workflows/bilanz.yml`:
```yaml
name: bilanz
on:
  schedule:
    - cron: '15 20 * * 1-5'    # 22:15 MESZ, Heartbeat
  workflow_dispatch: {}
jobs:
  send:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env:
      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
    steps:
      - uses: actions/checkout@v4
        with: {ref: main}
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -r requirements.txt
      - run: git pull --rebase || true
      - run: python scripts/send_bilanz.py
```

- [ ] **Step 4: Tests grün** — Run: `.venv/bin/pytest tests/test_workflows.py -v` — Expected: 1 passed.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "ci: GitHub-Actions-Workflows (Tests, Nacht-Scan, Beobachter, Depesche, Bilanz)"`

---

### Task 18: README & Inbetriebnahme-Checkliste

**Files:**
- Create: `README.md`

- [ ] **Step 1: README schreiben** — Inhalt (auf Deutsch, vollständig ausformulieren):

1. **Was ist TrainSpotter** — 3 Sätze (Momentum-Scanner, zwei Listen, Paper-Trading), Verweis auf Spec + Disclaimer „Analyse, keine Anlageberatung".
2. **Einmalige Einrichtung** (Checkliste zum Abhaken):
   - GitHub-Repo **öffentlich** anlegen, Code pushen
   - Telegram: mit @BotFather Bot erstellen → `TELEGRAM_BOT_TOKEN`; Bot anschreiben, dann `https://api.telegram.org/bot<TOKEN>/getUpdates` aufrufen → `chat.id` = `TELEGRAM_CHAT_ID`
   - Finnhub: kostenlosen Account auf finnhub.io → `FINNHUB_API_KEY`
   - Claude: lokal `claude setup-token` ausführen → `CLAUDE_CODE_OAUTH_TOKEN`
   - Alle 4 Werte als Repo-Secrets hinterlegen (Settings → Secrets and variables → Actions)
   - Actions aktivieren; Test: Workflow `depesche` manuell starten (`workflow_dispatch`) → Nachricht muss ankommen; alternativ lokal `python scripts/send_test_message.py`
3. **Betrieb** — Zeitplan-Tabelle (Nacht-Scan 07:00, Depesche 08:45, Beobachter EU 09:00–17:30, US 15:30–22:00, Bilanz 22:15, alles MESZ); Heartbeat-Regel: „Bleibt Depesche oder Bilanz aus → System steht, Actions-Log ansehen."
4. **Backtest** — `python scripts/run_backtest.py --market eu --years 3`; erst Regeln validieren, dann live vertrauen.
5. **Wartung/Backlog** — Feiertagslisten jährlich pflegen (`calendar_utils.py`); Winterzeit: Crons in den Workflows ggf. 1 h schieben; MDAX/SDAX-Erweiterung (`config/universe_de.csv`); US-Backtest auf 500 Titel gekappt; Score-Gewichte nach 4–8 Wochen Paper-Trading anhand `state/history/trades_*.csv` nachkalibrieren.

- [ ] **Step 2: Verifizieren** — Run: `.venv/bin/pytest -q` (Gesamtsuite grün) und `git status` (sauber nach Commit).
- [ ] **Step 3: Commit** — `git add -A && git commit -m "docs: README mit Inbetriebnahme-Checkliste"`

---

## Verifikation nach Abschluss aller Tasks

1. `pytest -q` — komplette Suite grün, ohne Netzzugriff.
2. `python scripts/run_dry_run.py` — simulierter Handelstag druckt Alert + Schließung, `{"alerts": 1, ...}`.
3. Manuell (mit echten Secrets, lokal): `python scripts/send_test_message.py` → Telegram-Nachricht kommt an.
4. Nach Push: `tests`-Workflow grün; `night-scan` und `depesche` einmal per `workflow_dispatch` starten und Ergebnis in Telegram prüfen.
