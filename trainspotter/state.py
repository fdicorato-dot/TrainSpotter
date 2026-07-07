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
