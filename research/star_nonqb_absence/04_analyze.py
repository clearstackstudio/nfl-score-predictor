"""Step 4: star non-QB absence bias analysis (per pre-registration).

Unit of analysis: team-game observation (exactly one shorthanded team).
  residual(team) = actual_margin(team perspective) - predicted_margin(team perspective)
Negative residual = model OVERRATES the shorthanded team (expected direction).

Tests: two-sided one-sample t-test vs 0, 95% CI in points.
Decision rule: |mean| >= 1.0 pt AND p < 0.05 on PRIMARY -> evidence; else NULL.
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from scipy import stats

OUT = Path(__file__).resolve().parent
RESID = OUT.parent / "new_coach_bias" / "residuals.csv"
TG = OUT / "absences_teamgame.csv"
STAR = OUT / "absences_starlevel.csv"
RESULTS = OUT / "RESULTS.md"


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


def fmt(name: str, r: dict) -> str:
    flag = "  <-- CLEARS BAR (|bias|>=1.0, p<0.05)" if abs(r["mean"]) >= 1.0 and r["p"] < 0.05 else ""
    return (f"{name}: n={r['n']:,}  mean={r['mean']:+.3f}  "
            f"95%CI=[{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}]  p={r['p']:.4f}{flag}")


def main() -> None:
    tg = pd.read_csv(TG)
    star = pd.read_csv(STAR)
    res = pd.read_csv(RESID)
    res["week_num"] = pd.to_numeric(res["week"], errors="coerce")
    res = res[res["week_num"].notna()].copy()

    lines: list[str] = []
    def emit(s: str = ""):
        print(s)
        lines.append(s)

    emit("# Results: star non-QB absence bias study (NFL)")
    emit()
    emit("Date: 2026-10-10. Pre-registration: "
         "`~/workspace/goals/ultimate-multi-sport-prediction-model/files/star-nonqb-absence-preregistration.md` "
         "(written before any game data was touched). Research only — no model changes.")
    emit()

    # ---- sanity checks ----
    emit("## Sanity checks")
    # baseline: all team-game residuals ~ 0. Build from residuals.csv both sides.
    both = pd.concat([
        res.assign(team=res["team_home"], r=res["actual_margin"] - res["our_margin"]),
        res.assign(team=res["team_away"], r=-(res["actual_margin"] - res["our_margin"])),
    ])
    base = both["r"]
    emit(f"- Baseline mean residual over all {len(base):,} team-games: {base.mean():+.4f} (|.|<0.15 required)")
    emit(f"- Residual SD: {base.std(ddof=1):.2f} (published scale ~13.7)")
    emit(f"- Primary sample: {len(tg):,} star-absence team-games")
    emit(f"- Star-seasons with >=1 missed game: {star[['player_slug','season']].drop_duplicates().shape[0]:,}")
    emit(f"- Unique stars ever absent: {star['player_slug'].nunique():,}")
    emit()

    # ---- tests ----
    emit("## Tests (two-sided t-test vs 0; negative = model overrates shorthanded team)")
    emit()
    results = {}
    results["primary"] = ttest_ci(tg["resid"])
    emit("- " + fmt("PRIMARY: all star-absence team-games", results["primary"]))
    early = tg[tg["early"] == 1]
    late = tg[tg["early"] == 0]
    results["early"] = ttest_ci(early["resid"])
    results["late"] = ttest_ci(late["resid"])
    emit("- " + fmt("Secondary: early-absence (streak<=4)", results["early"]))
    emit("- " + fmt("Secondary: late-absence (streak>=5)", results["late"]))
    for grp in ["skill", "ol", "defense"]:
        sub = star[star["pos_group"] == grp]
        results[f"pos_{grp}"] = ttest_ci(sub["resid"])
        emit("- " + fmt(f"Secondary: position group {grp} (star-level rows)", results[f"pos_{grp}"]))
    emit()

    # ---- robustness ----
    emit("## Robustness")
    loo_means = []
    for season, g in tg.groupby("season"):
        loo_means.append(tg[tg["season"] != season]["resid"].mean())
    emit(f"- Leave-one-season-out primary means: [{min(loo_means):+.3f}, {max(loo_means):+.3f}]")
    no_strike = tg[~tg["season"].isin([1982, 1987])]
    rs = ttest_ci(no_strike["resid"])
    emit("- Excluding strike seasons (1982/1987): " + fmt("primary", rs))
    dose1 = tg[tg["n_stars_out"] == 1]["resid"]
    dose2 = tg[tg["n_stars_out"] >= 2]["resid"]
    emit("- Dose-response (descriptive): 1 star out " + fmt("", ttest_ci(dose1)).split(": ", 1)[1]
         + f" | 2+ stars out n={len(dose2):,} " + fmt("", ttest_ci(dose2)).split(": ", 1)[1])
    # ATS descriptive: model picks in star-absence games. Merge team-games back to
    # residuals for ats_pick/picked_home; evaluate from shorthanded team's side.
    m = tg.merge(
        res[["season", "week_num", "team_home", "team_away", "ats_pick", "picked_home"]],
        left_on=["season", "week"], right_on=["season", "week_num"], how="left",
    )
    # keep the row where our team is home or away
    m = m[((m["team"] == m["team_home"]) | (m["team"] == m["team_away"]))]
    # deduplicate: each team-game joins exactly one game row (verify)
    m["pick_on_us"] = ((m["team"] == m["team_home"]) & (m["picked_home"] == 1)) | \
                      ((m["team"] == m["team_away"]) & (m["picked_home"] == 0))
    pk = m[m["ats_pick"].isin(["win", "loss", "push"])].copy()
    # result from the perspective of the side the model picked
    def pick_result(r):
        if r["ats_pick"] == "push":
            return "push"
        won = r["ats_pick"] == "win"
        picked_us = r["pick_on_us"]
        # model picked us and won, or picked against us and lost -> good for us
        return "win" if (won == picked_us) else "loss"
    pk["our_result"] = pk.apply(pick_result, axis=1)
    w = int((pk["our_result"] == "win").sum()); l = int((pk["our_result"] == "loss").sum())
    p = int((pk["our_result"] == "push").sum())
    dec = w + l
    emit(f"- ATS descriptive: {len(pk):,} star-absence team-games had a model pick; "
         f"shorthanded-team side went {w}-{l}-{p}" +
         (f" = {w/dec:.1%}" if dec else "") + " (context only)")
    emit()

    # ---- verdict ----
    emit("## Verdict")
    prim = results["primary"]
    if abs(prim["mean"]) >= 1.0 and prim["p"] < 0.05:
        emit("**EVIDENCE** (per pre-registered decision rule): the primary test cleared "
             f"the |1.0|-point bar (mean {prim['mean']:+.3f}, p={prim['p']:.4f}). "
             "A calibrated non-QB absence adjustment is worth proposing to Bryant. "
             "Nothing ships without his yes.")
        verdict = "EVIDENCE"
    else:
        emit("**NULL** (per pre-registered decision rule): the primary test did not clear "
             f"the |1.0|-point bar (mean {prim['mean']:+.3f}, p={prim['p']:.4f}). "
             "**Do not add a non-QB injury feature.** File with the other killed ideas.")
        verdict = "NULL"
    emit()
    emit("## Deviations from pre-registration (documented)")
    emit("(none yet — fill in if any)")
    emit()
    emit("## Files")
    emit("- Scripts: `research/star_nonqb_absence/01_scrape_allpro.py`, `02_scrape_gamelogs.py`, "
         "`03_build_absences.py`, `04_analyze.py`")
    emit("- Data: `allpro_stars.csv`, `star_gameweeks.csv`, `gamelog_completed.txt`, "
         "`absences_teamgame.csv`, `absences_starlevel.csv`, `join_audit.txt`")
    emit("- No `src/` or production files touched.")

    RESULTS.write_text("\n".join(lines))
    print(f"\nwrote {RESULTS} — verdict: {verdict}")


if __name__ == "__main__":
    main()
