"""H-P1: parlay leg-policy simulation over frame B (2014-2025).

Faithful to cfb_weekly_picks.py: leg pool = spread picks (|edge|>=0.5)
and total picks (1.0<=|edge|<=8.5 circuit), each leg's probability =
recalibrate(Phi(|edge|/sd)) with the SDs the live system loads from
data/cfb/cfb_backtest.json; current policy takes the top-3 legs by
probability (min 2). Book payouts: +260 (2 legs), +600 (3 legs).

Push handling (standard book behavior): a pushed leg drops out; a 3-leg
with one push pays as a 2-leg (+260), a 2-leg with one push pays as a
straight -110 bet (+0.909/unit), all legs pushed = refund.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.append(str(REPO / "src"))
from recalibration import recalibrate  # noqa: E402

CFG = json.loads((REPO / "data" / "cfb" / "cfb_backtest.json").read_text())
MARGIN_SD, TOTAL_SD = CFG["margin_sd"], CFG["total_sd"]
BOOK = {2: 2.6, 3: 6.0}  # profit per unit at +260 / +600


def ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def leg_outcome(resid):
    if abs(resid) < 0.01:
        return "P"
    return "W" if resid > 0 else "L"  # resid pre-signed per leg below


def build_legs(df):
    legs = []
    for r in df.itertuples():
        base = {"game_id": r.game_id, "season": r.season,
                "week_key": (r.season, r.season_type, r.week_true)}
        se = r.our_margin - r.line_margin
        if abs(se) >= 0.5:
            resid = (r.actual_margin - r.line_margin) * (1 if se > 0 else -1)
            legs.append({**base, "market": "spread",
                         "prob": recalibrate(ncdf(abs(se) / MARGIN_SD),
                                             "cfb", "ats"),
                         "edge": abs(se), "outcome": leg_outcome(resid)})
        te = r.our_total - r.line_total
        if 1.0 <= abs(te) <= 8.5:
            resid = (r.actual_total - r.line_total) * (1 if te > 0 else -1)
            legs.append({**base, "market": "total",
                         "prob": recalibrate(ncdf(abs(te) / TOTAL_SD),
                                             "cfb", "totals"),
                         "edge": abs(te), "outcome": leg_outcome(resid)})
    return pd.DataFrame(legs)


def settle(sel):
    """(profit_book, profit_fair, outright_win) for one selected parlay."""
    if any(l["outcome"] == "L" for l in sel):
        return -1.0, -1.0, False
    wins = [l for l in sel if l["outcome"] == "W"]
    if not wins:
        return 0.0, 0.0, False
    if len(wins) == len(sel):
        book = BOOK[len(sel)]
    elif len(wins) == 2:
        book = BOOK[2]
    else:
        book = 100 / 110
    p_wins = math.prod(l["prob"] for l in wins)
    fair = 1 / p_wins - 1 if p_wins > 0 else 0.0
    return book, fair, len(wins) == len(sel)


def simulate(legs, policy):
    rows = []
    for wk, g in legs.groupby("week_key"):
        if policy == "spread_only":
            pool = g[g.market == "spread"]
        else:
            pool = g
        pool = pool.sort_values("prob", ascending=False)
        sel = pool.head(3)
        if len(sel) < 2:
            continue
        sel = [dict(r) for r in sel.to_dict("records")]
        combined = math.prod(l["prob"] for l in sel)
        if policy == "ev_gate":
            breakeven = 1 / (1 + BOOK[len(sel)])
            if combined < breakeven:
                continue
        pb, pf, win = settle(sel)
        rows.append({"season": wk[0], "n_legs": len(sel),
                     "markets": "+".join(sorted(l["market"] for l in sel)),
                     "combined": combined, "profit_book": pb,
                     "profit_fair": pf, "win": win})
    return pd.DataFrame(rows)


def report(name, sim):
    if sim.empty:
        print(f"  {name}: no parlays placed")
        return
    n = len(sim)
    print(f"  {name}: parlays={n}  outright hits={int(sim.win.sum())} "
          f"({sim.win.mean():.1%})  book ROI/unit={sim.profit_book.mean():+.3f} "
          f"(total {sim.profit_book.sum():+.1f})  "
          f"fair-odds ROI/unit={sim.profit_fair.mean():+.3f}")
    mix = sim.groupby("n_legs").agg(n=("win", "size"),
                                    hit=("win", "mean"),
                                    roi=("profit_book", "mean"))
    for nl, r in mix.iterrows():
        print(f"    {nl}-leg: n={int(r.n)} hit {r.hit:.1%} ROI {r.roi:+.3f}")


def main():
    df = pd.read_parquet(HERE / "frame_B.parquet")
    meta = pd.read_parquet(HERE / "game_meta.parquet")
    df = df.merge(meta, on="game_id", how="left")
    df = df[df.season.between(2014, 2025)]
    legs = build_legs(df)
    print(f"legs: {len(legs)} "
          f"(spread {int((legs.market == 'spread').sum())}, "
          f"total {int((legs.market == 'total').sum())})")
    print(f"leg win rates: spread "
          f"{(legs[legs.market == 'spread'].outcome == 'W').mean():.1%}, total "
          f"{(legs[legs.market == 'total'].outcome == 'W').mean():.1%}")
    print("\n=== H-P1 policies ===")
    sims = {}
    for name, pol in (("(a) current top-3 any market", "current"),
                      ("(b) spread legs only", "spread_only"),
                      ("(d) current pool + EV gate", "ev_gate")):
        sims[name] = simulate(legs, pol)
        report(name, sims[name])
    cur = sims["(a) current top-3 any market"]
    print("\n  (a) per-season:")
    for s, d in cur.groupby("season"):
        print(f"    {s}: n={len(d)} hit {d.win.mean():.1%} "
              f"ROI {d.profit_book.mean():+.3f}")
    print("\n  (a) market mix of selected legs:")
    print(cur.markets.value_counts().to_string())
    # leg-pool quality by recalibrated prob band (context for policy design)
    legs["band"] = pd.cut(legs.prob, [0.5, 0.51, 0.52, 0.53, 1.0])
    print("\n  leg outcomes by recalibrated prob band:")
    print(legs.groupby("band", observed=True).outcome
          .apply(lambda s: f"n={len(s)} W{(s == 'W').mean():.1%}").to_string())


if __name__ == "__main__":
    main()
