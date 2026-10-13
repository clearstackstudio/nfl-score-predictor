"""Step 2: classify new-coach seasons from coaches_raw.csv -> new_coach_seasons.csv

Rules (per pre-registration):
- Primary population: single-coach seasons (multi_coach == 0).
- new_coach = this season's coach slug not in the previous season's slug set.
- Manual corrections (interim promoted to full-time counts as new):
    * DAL 2011 Garrett  (interim 2010 -> full-time 2011)
    * JAX 2017 Marrone  (interim 2016 -> full-time 2017)
  Verified against the scraped data below; add more only with a documented source.
- is_retread: coach slug previously head-coached a DIFFERENT franchise
  (any earlier season, full or interim tenure).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent
RAW = OUT / "coaches_raw.csv"
CSV = OUT / "new_coach_seasons.csv"

# (franchise, season) forced to new_coach=1: interim promoted to full-time.
MANUAL_NEW = {("dal", 2011), ("jax", 2017)}


def main() -> None:
    df = pd.read_csv(RAW).sort_values(["franchise", "season"]).reset_index(drop=True)

    # slug -> list of (franchise, season) coached, for retread detection
    df["slugs"] = df["coach_slugs"].apply(lambda s: [x for x in str(s).split("|") if x])
    seen: dict[str, list[tuple[str, int]]] = {}
    for _, r in df.iterrows():
        for slug in r["slugs"]:
            seen.setdefault(slug, []).append((r["franchise"], int(r["season"])))

    rows = []
    for f, g in df.groupby("franchise"):
        g = g.sort_values("season").reset_index(drop=True)
        prev_slugs: set[str] = set()
        for _, r in g.iterrows():
            season = int(r["season"])
            slugs = r["slugs"]
            single = len(slugs) == 1
            slug = slugs[0] if single else ""
            name = str(r["coach_names"]).split("|")[0] if single else ""
            if single:
                new = int(slug not in prev_slugs)
                if (f, season) in MANUAL_NEW:
                    new = 1
                # retread: coached a different franchise in an earlier season
                retread = int(
                    any(ff != f and ss < season for ff, ss in seen.get(slug, []))
                )
            else:
                new, retread = 0, 0  # multi-coach years excluded from primary
            rows.append(
                {
                    "franchise": f,
                    "season": season,
                    "team_name": r["team_name"],
                    "coach_slug": slug,
                    "coach_name": name,
                    "single_coach": int(single),
                    "is_new_coach": new,
                    "is_retread": retread,
                }
            )
            prev_slugs = set(slugs)

    out = pd.DataFrame(rows)
    out.to_csv(CSV, index=False)

    new = out[out["is_new_coach"] == 1]
    print(f"new-coach team-seasons: {len(new)}")
    print(f"  retreads: {int(new['is_retread'].sum())}, first-timers: {int((1 - new['is_retread']).sum())}")
    print(f"  seasons covered: {out['season'].min()}-{out['season'].max()}")
    print(f"  multi-coach seasons excluded: {int((out['single_coach'] == 0).sum())}")
    # manual-correction audit: any other interim-promoted pattern?
    print("\nAll new-coach seasons (audit):")
    for _, r in new.iterrows():
        tag = "RETREAD" if r["is_retread"] else "first-time"
        print(f"  {r['season']} {r['team_name']:<28} {r['coach_name']:<18} {tag}")


if __name__ == "__main__":
    main()
