"""Step 4: new-coach bias analysis (per pre-registration).

Unit of analysis: team-game observation.
  residual(team) = actual_margin(team perspective) - predicted_margin(team perspective)
Primary sample: games with exactly one new-coach team -> that team's residual.
Tests: two-sided one-sample t-test vs 0, 95% CI in points.
Decision rule: |mean| >= 1.0 pt AND p < 0.05 on primary -> evidence; else NULL.
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from scipy import stats

OUT = Path(__file__).resolve().parent
RESID = OUT / "residuals.csv"
COACH = OUT / "new_coach_seasons.csv"


def ttest_ci(x: pd.Series) -> dict:
    x = x.dropna()
    n = len(x)
    mean = x.mean()
    sd = x.std(ddof=1)
    se = sd / math.sqrt(n)
    t = mean / se if se > 0 else float("nan")
    p = 2 * (1 - stats.t.cdf(abs(t), n - 1))
    tcrit = stats.t.ppf(0.975, n - 1)
    return {
        "n": n, "mean": mean, "sd": sd, "se": se,
        "ci_lo": mean - tcrit * se, "ci_hi": mean + tcrit * se, "p": p,
    }


def report(name: str, r: dict) -> None:
    flag = ""
    if abs(r["mean"]) >= 1.0 and r["p"] < 0.05:
        flag = "  <-- CLEARS BAR (|bias|>=1.0, p<0.05)"
    print(
        f"{name}: n={r['n']:,}  mean={r['mean']:+.3f}  "
        f"95%CI=[{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}]  p={r['p']:.4f}{flag}"
    )


def main() -> None:
    g = pd.read_csv(RESID)
    c = pd.read_csv(COACH)

    # regular season only: numeric weeks
    g["week_num"] = pd.to_numeric(g["week"], errors="coerce")
    n_all = len(g)
    g = g[g["week_num"].notna()].copy()
    print(f"games: {n_all:,} total, {len(g):,} regular-season")

    # coach lookup: (team_name, season) -> (is_new_coach, is_retread, multi_coach)
    # Multi-coach seasons are INCLUDED with is_new_coach=0 (they are not new-coach
    # team-games, but their games must stay in the sample so the baseline stays
    # unbiased and the "exactly one new-coach team" game filter works correctly).
    # Only single_coach==1 rows can have is_new_coach==1.
    coach = {
        (r["team_name"], int(r["season"])): (
            int(r["is_new_coach"]), int(r["is_retread"]), int(r["single_coach"] == 0),
        )
        for _, r in c.iterrows()
    }

    # melt to team-game observations
    rows = []
    for _, r in g.iterrows():
        hr = float(r["actual_margin"]) - float(r["our_margin"])  # home perspective
        for team, is_home in ((r["team_home"], 1), (r["team_away"], 0)):
            resid = hr if is_home else -hr
            key = (team, int(r["season"]))
            nc, rt, mc = coach.get(key, (None, None, None))
            rows.append(
                {
                    "season": int(r["season"]),
                    "week": float(r["week_num"]),
                    "team": team,
                    "is_home": is_home,
                    "residual": resid,
                    "is_new_coach": nc,
                    "is_retread": rt,
                    "multi_coach": mc,
                    "ats_pick": r["ats_pick"],
                    "picked_home": r["picked_home"],
                    "actual_margin": float(r["actual_margin"]),
                    "line_margin": float(r["line_margin"]),
                }
            )
    t = pd.DataFrame(rows)
    unmatched = t["is_new_coach"].isna().sum()
    print(f"team-games: {len(t):,}, unmatched coach keys: {unmatched:,} "
          f"({unmatched / len(t):.2%})")
    if unmatched:
        print(t[t["is_new_coach"].isna()][["season", "team"]].drop_duplicates().head(20).to_string(index=False))
    t = t[t["is_new_coach"].notna()].copy()

    # ---- sanity checks ----
    print("\n--- sanity checks ---")
    b = ttest_ci(t["residual"])
    print(f"baseline mean residual (all team-games): {b['mean']:+.4f} (need |.|<0.15), sd={b['sd']:.2f} (need ~13.7)")
    nseasons = t[t["is_new_coach"] == 1][["season", "team"]].drop_duplicates()
    print(f"new-coach team-seasons: {len(nseasons)} (expect ~250-350)")
    print(f"new-coach team-games: {(t['is_new_coach'] == 1).sum():,}")

    # ---- primary: games with exactly one new-coach team ----
    print("\n--- primary + secondary tests ---")
    g2 = g.copy()
    # map new-coach flags onto games
    home_nc = g2.apply(lambda r: coach.get((r["team_home"], int(r["season"])), (0, 0))[0], axis=1)
    away_nc = g2.apply(lambda r: coach.get((r["team_away"], int(r["season"])), (0, 0))[0], axis=1)
    g2["home_nc"] = home_nc.fillna(0).astype(int)
    g2["away_nc"] = away_nc.fillna(0).astype(int)
    g2["n_new"] = g2["home_nc"] + g2["away_nc"]
    both = g2[g2["n_new"] == 2]
    print(f"both-teams-new-coach games: {len(both)} (descriptive only)")

    prim = g2[g2["n_new"] == 1].copy()
    # residual from the new-coach team's perspective
    prim["nc_resid"] = prim.apply(
        lambda r: (float(r["actual_margin"]) - float(r["our_margin"]))
        if r["home_nc"] == 1 else -(float(r["actual_margin"]) - float(r["our_margin"])),
        axis=1,
    )
    prim["nc_retread"] = prim.apply(
        lambda r: coach.get(
            (r["team_home"] if r["home_nc"] == 1 else r["team_away"], int(r["season"])),
            (0, 0),
        )[1],
        axis=1,
    )
    report("PRIMARY all new-coach games", ttest_ci(prim["nc_resid"]))

    early = prim[prim["week_num"] <= 4]
    late = prim[prim["week_num"] > 4]
    report("secondary weeks 1-4", ttest_ci(early["nc_resid"]))
    report("secondary weeks 5+", ttest_ci(late["nc_resid"]))
    report("secondary first-time HC", ttest_ci(prim[prim["nc_retread"] == 0]["nc_resid"]))
    report("secondary retread HC", ttest_ci(prim[prim["nc_retread"] == 1]["nc_resid"]))

    # ---- outlier check: leave-one-season-out ----
    print("\n--- leave-one-season-out (primary mean) ---")
    loos = []
    for s in sorted(prim["season"].unique()):
        m = prim[prim["season"] != s]["nc_resid"].mean()
        loos.append(m)
    print(f"range of LOO means: [{min(loos):+.3f}, {max(loos):+.3f}]")
    worst = prim.groupby("season")["nc_resid"].mean()
    print("most extreme seasons:")
    print(worst.reindex(worst.abs().sort_values(ascending=False).index).head(5).to_string())

    # ---- ATS descriptive ----
    print("\n--- ATS descriptive (new-coach team perspective, >=1.5pt edge picks) ---")
    pk = prim[prim["ats_pick"] != ""].copy()

    def team_cover(r):
        # game-level pick; convert to new-coach-team perspective
        home_covered = (float(r["actual_margin"]) - float(r["line_margin"])) > 0
        picked_home = r["picked_home"] == 1
        nc_is_home = r["home_nc"] == 1
        picked_nc = picked_home == nc_is_home
        nc_covered = home_covered if nc_is_home else not home_covered
        return "win" if picked_nc == nc_covered else "loss"

    pk["team_result"] = pk.apply(team_cover, axis=1)
    w = (pk["team_result"] == "win").sum()
    tot = len(pk)
    print(f"new-coach ATS on model picks: {w}-{tot - w} = {w / tot:.1%} (n={tot})")
    bk = g[(g["ats_pick"] == "win") | (g["ats_pick"] == "loss")]
    bw = (bk["ats_pick"] == "win").sum()
    print(f"baseline ATS on model picks: {bw / len(bk):.1%} (n={len(bk):,})")

    # ---- verdict ----
    print("\n--- verdict ---")
    pr = ttest_ci(prim["nc_resid"])
    if abs(pr["mean"]) >= 1.0 and pr["p"] < 0.05:
        print(f"EVIDENCE: primary bias {pr['mean']:+.2f} pts, p={pr['p']:.4f} — "
              "worth proposing an adjustment (needs Bryant's yes).")
    else:
        print(f"NULL: primary bias {pr['mean']:+.3f} pts, 95% CI "
              f"[{pr['ci_lo']:+.3f},{pr['ci_hi']:+.3f}], p={pr['p']:.4f} — "
              "do not add a coaching feature.")


if __name__ == "__main__":
    main()
