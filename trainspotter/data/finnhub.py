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
