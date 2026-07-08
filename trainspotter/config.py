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
WATCHLIST_QUOTA = {("us", "spekulativ"): 70, ("us", "konservativ"): 40,
                   ("eu", "konservativ"): 25, ("eu", "spekulativ"): 15}   # Summe = WATCHLIST_SIZE
ADR_MIN_KONS = 1.5              # Ø-Tagesspanne %
ADR_MIN_SPEC = 3.0

# Live-Trigger
TRIGGER_VOL_RATIO = 2.0         # zeitanteiliges Volumen
INDEX_FILTER_PCT = -1.5         # Index intraday darunter -> nur spek. + Warnung
MISSED_TRAIN_PCT = {"konservativ": 4.0, "spekulativ": 6.0}
STOP_PCT = {"konservativ": 3.0, "spekulativ": 6.0}      # unter Ausbruchsniveau
TARGET1_PCT = {"konservativ": 4.0, "spekulativ": 10.0}  # über Einstieg
MAX_ALERTS_PER_LIST = 5
MAX_MISSED_PER_DAY = 3          # Tagesbudget für "Zug verpasst"-Meldungen

# Kumulatives Intraday-Volumenprofil (U-Kurve): (Sitzungsanteil, kumulierter Volumenanteil)
VOLUME_PROFILE = [(0.0, 0.0), (0.08, 0.12), (0.15, 0.20), (0.5, 0.52), (0.85, 0.80), (0.92, 0.88), (1.0, 1.0)]

# Paper-Trading
SLIPPAGE_PCT = {"konservativ": 0.2, "spekulativ": 0.75}
POSITION_SIZE_EUR = 1000.0
TRAIL_WINDOW_MIN = 30           # Trailing: Tief der letzten 30 Min
TRAIL_BUFFER_PCT = 0.5          # Stop knapp UNTER dem Tief
MAX_HOLD_DAYS_KONS = 3

# Betrieb
CYCLE_SECONDS = {"us": 15, "eu": 120}   # US: Finnhub-Ratenbremse taktet den Zyklus selbst
US_VOLUME_REFRESH_CYCLES = 5    # Yahoo-Volumen-Cache alle N Zyklen
LISTEN = ("konservativ", "spekulativ")

# Indizes je Markt (Yahoo-Symbole)
INDEX_SYMBOL = {"us": "^GSPC", "eu": "^GDAXI"}

DISCLAIMER = "Hinweis: Analyse, keine Anlageberatung."
REPORT_URL_BASE = "https://fdicorato-dot.github.io/TrainSpotter/reports"
