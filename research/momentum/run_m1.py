#!/usr/bin/env python3
"""M1 momentum/streak test — implements PREREGISTRATION.md exactly."""
import numpy as np
import pandas as pd

CSV = "/home/hatch/workspace/goals/ultimate-multi-sport-prediction-model/hidden_files/pattern_study/nfl/nfl_walkforward_1980_2024.csv"

df = pd.read_csv(CSV, parse_dates=["date"])
df = df.sort_values(["date", "home_fr", "away_fr"]).reset_index(drop=True)

# Build streak + last-3 win% entering each game, strictly from prior games.
streak = {}          # franchise -> signed streak
recent = {}          # franchise -> list of last results (1 win, 0 loss, 0.5 tie)
rows = []
for _, g in df.iterrows():
    h, a = g["home_fr"], g["away_fr"]
    hs, as_ = streak.get(h, 0), streak.get(a, 0)
    hr, ar = recent.get(h, []), recent.get(a, [])
    h_l3 = np.mean(hr[-3:]) if hr else np.nan
    a_l3 = np.mean(ar[-3:]) if ar else np.nan
    rows.append((hs, as_, hs - as_, h_l3, a_l3,
                 (h_l3 - a_l3) if (hr and ar) else np.nan))
    # update AFTER recording (no leakage)
    m = g["actual_margin"]
    for team, won in ((h, m > 0), (a, m < 0)):
        tie = (m == 0)
        s = streak.get(team, 0)
        if tie:
            streak[team] = 0
        elif won:
            streak[team] = s + 1 if s > 0 else 1
        else:
            streak[team] = s - 1 if s < 0 else -1
        r = recent.setdefault(team, [])
        r.append(0.5 if tie else (1.0 if won else 0.0))

df[["home_streak", "away_streak", "streak_diff", "home_l3", "away_l3", "l3_diff"]] = rows

def ols(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    xm, ym = x.mean(), y.mean()
    b = ((x - xm) * (y - ym)).sum() / ((x - xm) ** 2).sum()
    a = ym - b * xm
    resid = y - (a + b * x)
    n = len(x)
    se = np.sqrt((resid ** 2).sum() / (n - 2) / ((x - xm) ** 2).sum())
    return a, b, b / se, n

disc = df[df.season <= 2014]
val = df[df.season >= 2015]
print(f"games total={len(df)} discovery={len(disc)} validation={len(val)}")

for name, d in (("DISCOVERY 1980-2014", disc), ("VALIDATION 2015-2024", val)):
    a, b, z, n = ols(d["streak_diff"], d["margin_resid"])
    print(f"{name}: slope(streak_diff -> margin_resid) = {b:+.4f} pts/streak-game, z={z:+.2f}, n={n}")
    a3, b3, z3, n3 = ols(d["l3_diff"].fillna(0), d["margin_resid"])
    print(f"  descriptive last3-winpct-diff slope = {b3:+.4f}, z={z3:+.2f}")

# KEEP gate 2: discovery-fitted adjustment on validation RMSE
_, b_disc, _, _ = ols(disc["streak_diff"], disc["margin_resid"])
base_rmse = np.sqrt((val["margin_resid"] ** 2).mean())
adj_resid = val["actual_margin"] - (val["our_margin"] + b_disc * val["streak_diff"])
adj_rmse = np.sqrt((adj_resid ** 2).mean())
print(f"validation margin RMSE: base={base_rmse:.4f}  streak-adjusted(b_disc={b_disc:+.4f})={adj_rmse:.4f}  delta={adj_rmse-base_rmse:+.4f}")

# Secondary descriptive: ATS picks |edge|>=1.5, streak agreement
picks = val[(val["spread_edge"].abs() >= 1.5) & val["ats_win"].isin(["win", "loss"])].copy()
picks["pick_home"] = picks["ats_pick"] == "home"
picks["streak_sign"] = np.sign(picks["streak_diff"])
picks["agree"] = np.where(picks["pick_home"], picks["streak_sign"] > 0, picks["streak_sign"] < 0)
picks["neutral"] = picks["streak_sign"] == 0
for label, sub in (("streak agrees with pick", picks[picks.agree & ~picks.neutral]),
                   ("streak opposes pick", picks[~picks.agree & ~picks.neutral]),
                   ("streak neutral (one/both at 0)", picks[picks.neutral])):
    if len(sub):
        w = (sub["ats_win"] == "win").mean()
        print(f"ATS validation picks: {label}: {w:.1%} (n={len(sub)})")

# Secondary descriptive: SU — streak-favored vs model-favored
v = val.copy()
v["home_won"] = v["actual_margin"] > 0
sf = v[v["streak_diff"] != 0]
print(f"SU validation: streak-favored team won {(sf['home_won'] == (sf['streak_diff'] > 0)).mean():.1%} (n={len(sf)})")
mf = v[v["our_margin"] != 0]
print(f"SU validation: model-favored team won {(mf['home_won'] == (mf['our_margin'] > 0)).mean():.1%} (n={len(mf)})")
both = v[(v["streak_diff"] != 0)]
dis = both[np.sign(both["streak_diff"]) != np.sign(both["our_margin"])]
print(f"SU validation where streak and model disagree: streak side won {(dis['home_won'] == (dis['streak_diff'] > 0)).mean():.1%} (n={len(dis)})")
