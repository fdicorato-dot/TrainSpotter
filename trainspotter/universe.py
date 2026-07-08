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


def parse_nasdaq_names(text: str) -> dict[str, str]:
    """Symbol -> Klarname, gleiche Filter wie parse_nasdaq_file; Suffixe wie
    ' - Common Stock' werden am ersten ' - ' abgeschnitten."""
    names = {}
    for line in text.splitlines()[1:]:
        parts = line.split("|")
        if len(parts) < 7 or line.startswith("File Creation"):
            continue
        sym, name, test_issue, etf = parts[0], parts[1], parts[3], parts[6]
        if test_issue == "N" and etf == "N" and sym.isalpha():
            names[sym] = name.split(" - ")[0].strip()
    return names


def load_us_names() -> dict[str, str]:
    names: dict[str, str] = {}
    for url in NASDAQ_URLS:
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            names |= parse_nasdaq_names(r.text)
        except requests.RequestException:
            continue                                   # eine Quelle darf ausfallen
    return names


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


def load_de_names(path: str = "config/universe_de.csv") -> dict[str, str]:
    with open(path, newline="") as f:
        return {row["ticker"]: row.get("name") or row["ticker"]
                for row in csv.DictReader(f)}
