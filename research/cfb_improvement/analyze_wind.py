"""H-T2: CFB-specific wind hinge, calibrated walk-forward (frame B).

Wind = Open-Meteo ERA5 hourly at the home school's stadium, kickoff hour
(UTC floor) — same source/method as cfb/fetch_cfb_wind.py, extended to
2014-2025 (wind_2014_2025.parquet, fetched for this study). Outdoor,
non-neutral games only (neutral-site venues are not in the stadium map);
dome schools get no adjustment by construction.

Design: for each evaluation season Y in 2016-2025, grid-search the hinge
(threshold, slope, cap) minimizing total RMSE on outdoor games from
seasons < Y only, then apply to season Y. Adoption bar (pre-registered):
outdoor total RMSE improves in a majority of evaluation seasons AND
overall, without degrading overall totals.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
STADIUMS = json.loads((REPO / "cfb" / "cfb_stadiums.json").read_text())
THRESHOLDS = [10, 12, 14, 16]
SLOPES = [0.25, 0.5, 0.75, 1.0]
CAPS = [4, 6, 8]


def hinge(wind, thr, slope, cap):
    return -np.minimum(cap, np.maximum(0.0, wind - thr) * slope)


def grade(edge, resid, thr=1.0, circuit=8.5):
    m = (edge.abs() >= thr) & (edge.abs() <= circuit)
    e, r = edge[m], resid[m]
    w = int(((r.abs() >= 0.01) & ((r > 0) == (e > 0))).sum())
    p = int((r.abs() < 0.01).sum())
    return w, int(len(r) - w - p), p


def pct(w, l):
    return w / (w + l) if (w + l) else float("nan")


def main():
    df = pd.read_parquet(HERE / "frame_B.parquet")
    df = df[df.season.between(2014, 2025)].copy()
    wind = pd.read_parquet(HERE / "wind_2014_2025.parquet")
    wser = wind.set_index(["school", "time"])["wind_mph"]

    def get_wind(r):
        if r.neutral:
            return np.nan, "neutral"
        stad = STADIUMS.get(r.home)
        if stad is None:
            return np.nan, "no_stadium"
        if stad["dome"]:
            return 0.0, "dome"
        kickoff = pd.Timestamp(r.date).floor("h")
        try:
            return float(wser.loc[(r.home, kickoff)]), "outdoor"
        except KeyError:
            return np.nan, "no_wind"

    info = [get_wind(r) for r in df.itertuples()]
    df["wind"] = [x[0] for x in info]
    df["venue"] = [x[1] for x in info]
    print("venue coverage:", df.venue.value_counts().to_dict())
    out = df[df.venue == "outdoor"].copy()
    print(f"outdoor games with wind: {len(out)} "
          f"({out.season.min()}-{out.season.max()}); "
          f"wind>=15mph: {int((out.wind >= 15).sum())}, "
          f"wind>=20mph: {int((out.wind >= 20).sum())}")

    out["bias"] = out.our_total - out.actual_total
    out["bucket"] = pd.cut(out.wind, [0, 5, 10, 15, 20, 100],
                           labels=["0-5", "5-10", "10-15", "15-20", "20+"])
    print("\nresidual bias (our_total - actual) by wind bucket, outdoor:")
    print(out.groupby("bucket", observed=True)["bias"]
          .agg(["count", "mean"]).round(2).to_string())

    # H2 cross-check on frame B, 2022-2024: verbatim NFL hinge.
    h2 = out[out.season.between(2022, 2024)]
    hi = h2[h2.wind >= 15]
    for lab, tot in (("raw", h2.our_total), ("NFL hinge", h2.our_total
                      + hinge(h2.wind, 10, 1.0, 8))):
        w, l, p = grade(tot - h2.line_total, h2.actual_total - h2.line_total)
        print(f"  H2 window {lab}: overall OU {w}-{l}-{p} "
              f"{pct(w, l):.1%}")
    for lab, tot in (("raw", hi.our_total), ("NFL hinge", hi.our_total
                      + hinge(hi.wind, 10, 1.0, 8))):
        w, l, p = grade(tot - hi.line_total, hi.actual_total - hi.line_total)
        print(f"  H2 window high-wind {lab}: OU {w}-{l}-{p} {pct(w, l):.1%} "
              f"bias {(tot - hi.actual_total).mean():+.2f}")

    def fit(fit_df):
        best, best_rmse = None, np.inf
        for thr in THRESHOLDS:
            for slope in SLOPES:
                for cap in CAPS:
                    adj = fit_df.our_total + hinge(fit_df.wind, thr, slope, cap)
                    rmse = np.sqrt(((adj - fit_df.actual_total) ** 2).mean())
                    if rmse < best_rmse:
                        best, best_rmse = (thr, slope, cap), rmse
        return best

    print("\nwalk-forward hinge fit (fit on prior seasons, eval 2016-2025):")
    imp_out = imp_all = 0
    tot_raw_se, tot_adj_se = [], []
    for y in range(2016, 2026):
        fit_df = out[out.season < y]
        ev = out[out.season == y]
        params = fit(fit_df)
        adj = ev.our_total + hinge(ev.wind, *params)
        r0 = np.sqrt(((ev.our_total - ev.actual_total) ** 2).mean())
        r1 = np.sqrt(((adj - ev.actual_total) ** 2).mean())
        imp_out += r1 < r0
        hi_m = ev.wind >= 15
        w0, l0, _ = grade(ev.our_total - ev.line_total,
                          ev.actual_total - ev.line_total)
        w1, l1, _ = grade(adj - ev.line_total, ev.actual_total - ev.line_total)
        hw0, hl0, _ = grade(ev[hi_m].our_total - ev[hi_m].line_total,
                            ev[hi_m].actual_total - ev[hi_m].line_total)
        hw1, hl1, _ = grade(adj[hi_m] - ev[hi_m].line_total,
                            ev[hi_m].actual_total - ev[hi_m].line_total)
        tot_raw_se.append(r0)
        tot_adj_se.append(r1)
        print(f"  {y}: params(thr,slope,cap)={params}  outdoor RMSE "
              f"{r0:.2f}->{r1:.2f}  OU {pct(w0, l0):.1%}->{pct(w1, l1):.1%}  "
              f"high-wind OU (n={hi_m.sum()}) {pct(hw0, hl0):.1%}"
              f"->{pct(hw1, hl1):.1%}")
    allfit = out[out.season < 2026]
    adj_all = allfit.our_total + hinge(
        allfit.wind, *fit(allfit)) if False else None
    print(f"  outdoor RMSE improved in {imp_out}/10 eval seasons")
    # Pooled: apply each season's own WF params to that season (true WF pool)
    pooled_adj, pooled_raw = [], []
    for y in range(2016, 2026):
        ev = out[out.season == y]
        params = fit(out[out.season < y])
        pooled_adj.append(ev.our_total + hinge(ev.wind, *params)
                          - ev.actual_total)
        pooled_raw.append(ev.our_total - ev.actual_total)
    pa = np.concatenate(pooled_adj)
    pr = np.concatenate(pooled_raw)
    print(f"  pooled WF (2016-2025 outdoor): RMSE "
          f"{np.sqrt((pr ** 2).mean()):.2f} -> {np.sqrt((pa ** 2).mean()):.2f}")
    best_all = fit(out)
    adj = out.our_total + hinge(out.wind, *best_all)
    print(f"  in-sample best params on all outdoor games: {best_all} "
          f"(descriptive only)  RMSE "
          f"{np.sqrt(((out.our_total - out.actual_total) ** 2).mean()):.2f} -> "
          f"{np.sqrt(((adj - out.actual_total) ** 2).mean()):.2f}")


if __name__ == "__main__":
    main()
