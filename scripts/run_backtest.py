"""Tages-Backtest: python scripts/run_backtest.py --market eu [--years 3]"""
import argparse
import trainspotter.config as cfg
from trainspotter import backtest, universe
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
    print(f"Übersprungen (Datumsversatz): {df.attrs.get('skipped', 0)} Titel")
    if df.empty:
        print("Keine Trades gefunden.")
    else:
        print(df.groupby("liste")["pnl_pct"].describe())
        wins = df[df.pnl_pct > 0]
        print(f"\nTrades: {len(df)} | Trefferquote: {len(wins) / len(df) * 100:.1f}% "
              f"| Ø PnL: {df.pnl_pct.mean():.2f}%")
        df.to_csv("state/history/backtest_result.csv", index=False)
