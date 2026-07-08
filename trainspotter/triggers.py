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
            "name": entry.get("name", entry["ticker"]),
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
                           sent_counts: dict[str, int], missed_sent: int = 0) -> list[dict]:
    fresh = [c for c in candidates if c["id"] not in alerts_sent]
    missed_budget = max(cfg.MAX_MISSED_PER_DAY - missed_sent, 0)
    out = sorted((c for c in fresh if c["status"] == "missed"),
                 key=lambda c: c["score"], reverse=True)[:missed_budget]
    budget = {l: cfg.MAX_ALERTS_PER_LIST - sent_counts.get(l, 0) for l in cfg.LISTEN}
    for c in sorted((c for c in fresh if c["status"] == "alert"),
                    key=lambda c: c["score"], reverse=True):
        if budget[c["liste"]] > 0:
            budget[c["liste"]] -= 1
            out.append(c)
    return out
