import argparse
from trainspotter.live_observer import run_session

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--market", choices=["us", "eu"], required=True)
    p.add_argument("--max-minutes", type=int, default=335)
    a = p.parse_args()
    run_session(a.market, a.max_minutes)
