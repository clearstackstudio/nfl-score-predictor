"""Hypothesis analyses for the CFB improvement study (non-wind, non-parlay).

Reads frame_B.parquet (chronological walk-forward) and frame_B8.parquet
(H-S3 shrinkage variant), joins game_meta.parquet, prints every table that
RESULTS.md needs. Seasons 2014-2025 are the test set; 2026 is reported
separately and never used for any fit.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TEST_SEASONS = list(range(2014, 2026))
BREAKEVEN = 0.5238  # -110


def z_vs(p_hat, n, p0=0.5):
    if n == 0:
        return float("nan")
    return (p_hat - p0) / math.sqrt(p0 * (1 - p0) / n)


def z_two(p1, n1, p2, n2):
    if n1 == 0 or n2 == 0:
        return float("nan")
    p = (p1 * n1 + p2 * n2) / (n1 + n2)
    return (p1 - p2) / math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))


def grade(edge, resid, thr):
    """W/L/P counts for picks with |edge| >= thr (resid = actual - line,
    signed so resid and edge agreeing = win)."""
    m = edge.abs() >= thr
    e, r = edge[m], resid[m]
    w = int(((r.abs() >= 0.01) & ((r > 0) == (e > 0))).sum())
    p = int((r.abs() < 0.01).sum())
    return w, int(len(r) - w - p), p


def pct(w, l):
    return w / (w + l) if (w + l) else float("nan")


def fmt_pct(x):
    return f"{x:.1%}" if x == x else "  -  "


def load(mode):
    df = pd.read_parquet(HERE / f"frame_{mode}.parquet")
    meta = pd.read_parquet(HERE / "game_meta.parquet")
    df = df.merge(meta, on="game_id", how="left")
    df["spread_edge"] = df.our_margin - df.line_margin
    df["total_edge"] = df.our_total - df.line_total
    df["mresid"] = df.actual_margin - df.line_margin
    df["tresid"] = df.actual_total - df.line_total
    df["min_gp"] = df[["home_gp", "away_gp"]].min(axis=1)
    return df


def season_table(df, label):
    print(f"\n=== Per-season baseline ({label}, published thresholds) ===")
    print(f"{'season':<7}{'games':>6}{'SU%':>7}{'mRMSE':>7}{'lnRMSE':>7}"
          f"{'ATS W-L-P':>14}{'ATS%':>7}{'tRMSE':>7}{'lnRMSE':>7}"
          f"{'OU W-L-P':>14}{'OU%':>7}")
    for s, d in df.groupby("season"):
        w, l, p = grade(d.spread_edge, d.mresid, 0.5)
        ow, ol, op = grade(d.total_edge, d.tresid, 1.0)
        print(f"{s:<7}{len(d):>6}"
              f"{((d.our_margin > 0) == (d.actual_margin > 0)).mean():>7.1%}"
              f"{np.sqrt(((d.our_margin - d.actual_margin) ** 2).mean()):>7.2f}"
              f"{np.sqrt(((d.line_margin - d.actual_margin) ** 2).mean()):>7.2f}"
              f"{f'{w}-{l}-{p}':>14}{fmt_pct(pct(w, l)):>7}"
              f"{np.sqrt(((d.our_total - d.actual_total) ** 2).mean()):>7.2f}"
              f"{np.sqrt(((d.line_total - d.actual_total) ** 2).mean()):>7.2f}"
              f"{f'{ow}-{ol}-{op}':>14}{fmt_pct(pct(ow, ol)):>7}")


def h_s1(df):
    print("\n=== H-S1: ATS by |spread edge| bucket and cumulative threshold ===")
    bounds = [0.5, 1, 2, 3, 4, 5, 7, 10, np.inf]
    for lo, hi in zip(bounds[:-1], bounds[1:]):
        m = (df.spread_edge.abs() >= lo) & (df.spread_edge.abs() < hi)
        d = df[m]
        w, l, p = grade(d.spread_edge, d.mresid, 0.0)
        print(f"  edge [{lo},{hi}): n={len(d):>5}  {w}-{l}-{p}  "
              f"ATS {fmt_pct(pct(w, l))}  z={z_vs(pct(w, l), w + l):+.2f}")
    print("  cumulative thresholds (per-season detail for promising ones):")
    for t in [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8, 10]:
        w, l, p = grade(df.spread_edge, df.mresid, t)
        print(f"  |edge|>={t}: n={w + l + p:>5}  {w}-{l}-{p}  "
              f"ATS {fmt_pct(pct(w, l))}  z50={z_vs(pct(w, l), w + l):+.2f}  "
              f"zBE={z_vs(pct(w, l), w + l, BREAKEVEN):+.2f}")
    for t in [2, 3, 4, 5]:
        per = []
        for s, d in df.groupby("season"):
            w, l, p = grade(d.spread_edge, d.mresid, t)
            per.append(f"{s}:{fmt_pct(pct(w, l))}(n{w + l})")
        print(f"  thr {t} per-season: " + " ".join(per))


def h_s2(df):
    print("\n=== H-S2: FCS opponents ===")
    n_fcs = int(((df.home_class != "fbs") | (df.away_class != "fbs")).sum())
    print(f"  backtest games (2014-2025) involving a non-FBS team: {n_fcs} "
          f"of {len(df)}")


def h_s3(df, df8):
    print("\n=== H-S3: ATS by games-played-prior (min of two teams) ===")
    for lo, hi, lab in [(0, 1, "0-1"), (2, 3, "2-3"), (4, 5, "4-5"),
                        (6, 99, "6+")]:
        d = df[(df.min_gp >= lo) & (df.min_gp <= hi)]
        w, l, p = grade(d.spread_edge, d.mresid, 0.5)
        print(f"  min_gp {lab}: n={len(d):>5}  {w}-{l}-{p}  "
              f"ATS {fmt_pct(pct(w, l))}  z={z_vs(pct(w, l), w + l):+.2f}")
    reg = df[df.season_type == "regular"]
    print("  by regular-season week:")
    for lo, hi, lab in [(1, 2, "wk1-2"), (3, 4, "wk3-4"), (5, 8, "wk5-8"),
                        (9, 12, "wk9-12"), (13, 16, "wk13+")]:
        d = reg[(reg.week_true >= lo) & (reg.week_true <= hi)]
        w, l, p = grade(d.spread_edge, d.mresid, 0.5)
        print(f"  {lab}: n={len(d):>5}  {w}-{l}-{p}  ATS {fmt_pct(pct(w, l))}")
    post = df[df.season_type == "postseason"]
    w, l, p = grade(post.spread_edge, post.mresid, 0.5)
    print(f"  postseason: n={len(post):>5}  {w}-{l}-{p}  ATS {fmt_pct(pct(w, l))}")
    print("  B8 (MIN_GAMES=8) vs B: overall and early (min_gp<=3):")
    for lab, base in (("all", df), ("early", df[df.min_gp <= 3])):
        var = df8[df8.game_id.isin(base.game_id)]
        w0, l0, p0 = grade(base.spread_edge, base.mresid, 0.5)
        w1, l1, p1 = grade(var.spread_edge, var.mresid, 0.5)
        print(f"  {lab}: B {w0}-{l0}-{p0} ({fmt_pct(pct(w0, l0))})  "
              f"B8 {w1}-{l1}-{p1} ({fmt_pct(pct(w1, l1))})")
    better = worse = same = 0
    for s, d in df.groupby("season"):
        v = df8[df8.season == s]
        w0, l0, _ = grade(d.spread_edge, d.mresid, 0.5)
        w1, l1, _ = grade(v.spread_edge, v.mresid, 0.5)
        dlt = pct(w1, l1) - pct(w0, l0)
        better += dlt > 0.001
        worse += dlt < -0.001
        same += abs(dlt) <= 0.001
    print(f"  B8 ATS better/worse/same seasons: {better}/{worse}/{same}")


def h_s4(df):
    print("\n=== H-S4: conference vs non-conference ATS ===")
    for lab, d in (("conference", df[df.conf_game]),
                   ("non-conference", df[~df.conf_game])):
        w, l, p = grade(d.spread_edge, d.mresid, 0.5)
        print(f"  {lab}: n={len(d):>5}  {w}-{l}-{p}  ATS {fmt_pct(pct(w, l))}  "
              f"z={z_vs(pct(w, l), w + l):+.2f}")
    c = df[df.conf_game]
    nc = df[~df.conf_game]
    wc, lc, _ = grade(c.spread_edge, c.mresid, 0.5)
    wn, ln, _ = grade(nc.spread_edge, nc.mresid, 0.5)
    print(f"  two-proportion z (conf vs non-conf): "
          f"{z_two(pct(wc, lc), wc + lc, pct(wn, ln), wn + ln):+.2f}")
    per = []
    for s, d in c.groupby("season"):
        w, l, p = grade(d.spread_edge, d.mresid, 0.5)
        per.append(f"{s}:{fmt_pct(pct(w, l))}(n{w + l})")
    print("  conf per-season: " + " ".join(per))


def totals_baseline(df):
    print("\n=== Totals baseline (frame B) ===")
    w, l, p = grade(df.total_edge, df.tresid, 1.0)
    print(f"  published rule |edge|>=1.0: {w}-{l}-{p}  OU {fmt_pct(pct(w, l))}")
    m = df.total_edge.abs() <= 8.5
    w, l, p = grade(df[m].total_edge, df[m].tresid, 1.0)
    print(f"  live rule (+circuit <=8.5): {w}-{l}-{p}  OU {fmt_pct(pct(w, l))}")
    for lab, d in (("over picks", df[df.total_edge > 0]),
                   ("under picks", df[df.total_edge < 0])):
        w, l, p = grade(d.total_edge, d.tresid, 1.0)
        print(f"  {lab}: n={w + l + p}  {w}-{l}-{p}  OU {fmt_pct(pct(w, l))}")
    bounds = [1, 2.5, 5, 8.5, np.inf]
    for lo, hi in zip(bounds[:-1], bounds[1:]):
        d = df[(df.total_edge.abs() >= lo) & (df.total_edge.abs() < hi)]
        w, l, p = grade(d.total_edge, d.tresid, 0.0)
        print(f"  edge [{lo},{hi}): n={len(d):>5}  {w}-{l}-{p}  OU {fmt_pct(pct(w, l))}")


def h_t4(df):
    print("\n=== H-T4: model total bias by season ===")
    df = df.assign(bias=df.our_total - df.actual_total,
                   lbias=df.line_total - df.actual_total)
    print(f"{'season':<7}{'model bias':>11}{'line bias':>10}{'n':>6}")
    for s, d in df.groupby("season"):
        print(f"{s:<7}{d.bias.mean():>11.2f}{d.lbias.mean():>10.2f}{len(d):>6}")
    pos = sum(d.bias.mean() > 0 for _, d in df.groupby("season"))
    print(f"  seasons with positive model bias: {pos}/{df.season.nunique()}; "
          f"overall bias {df.bias.mean():+.2f} (line {df.lbias.mean():+.2f})")
    print("  walk-forward expanding correction (fit on prior seasons only):")
    imp = 0
    for s in sorted(df.season.unique()):
        if s == df.season.min():
            continue
        hist = df[df.season < s]
        d = df[df.season == s]
        c = hist.bias.mean()
        raw_rmse = np.sqrt(((d.our_total - d.actual_total) ** 2).mean())
        cor = d.our_total - c
        cor_rmse = np.sqrt(((cor - d.actual_total) ** 2).mean())
        w0, l0, _ = grade(d.total_edge, d.tresid, 1.0)
        w1, l1, _ = grade(cor - d.line_total, d.tresid, 1.0)
        imp += cor_rmse < raw_rmse
        print(f"  {s}: c={c:+.2f}  RMSE {raw_rmse:.2f}->{cor_rmse:.2f}  "
              f"OU {fmt_pct(pct(w0, l0))}->{fmt_pct(pct(w1, l1))}")
    print(f"  seasons where WF correction improved RMSE: {imp}")


def h_t3(df):
    print("\n=== H-T3: shrinkage of PPA-sum toward epa_const ===")
    grid = [1.0, 0.95, 0.9, 0.85, 0.8, 0.7]
    for s in grid:
        t = df.epa_const + s * (df.our_total - df.epa_const)
        rmse = np.sqrt(((t - df.actual_total) ** 2).mean())
        w, l, p = grade(t - df.line_total, df.tresid, 1.0)
        print(f"  s={s}: total RMSE {rmse:.2f}  OU {w}-{l}-{p} {fmt_pct(pct(w, l))}")
    print("  walk-forward chosen s (min prior-season RMSE), per season:")
    imp_r = imp_o = 0
    for s in sorted(df.season.unique()):
        if s == df.season.min():
            continue
        hist, d = df[df.season < s], df[df.season == s]
        best = min(grid, key=lambda s_: np.sqrt(
            ((hist.epa_const + s_ * (hist.our_total - hist.epa_const)
              - hist.actual_total) ** 2).mean()))
        t = d.epa_const + best * (d.our_total - d.epa_const)
        r0 = np.sqrt(((d.our_total - d.actual_total) ** 2).mean())
        r1 = np.sqrt(((t - d.actual_total) ** 2).mean())
        w0, l0, _ = grade(d.total_edge, d.tresid, 1.0)
        w1, l1, _ = grade(t - d.line_total, d.tresid, 1.0)
        imp_r += r1 < r0
        imp_o += pct(w1, l1) > pct(w0, l0)
        print(f"  {s}: s*={best}  RMSE {r0:.2f}->{r1:.2f}  "
              f"OU {fmt_pct(pct(w0, l0))}->{fmt_pct(pct(w1, l1))}")
    print(f"  WF shrinkage improved RMSE in {imp_r} seasons, OU in {imp_o}")


def h_t1(df):
    print("\n=== H-T1: expected-plays variants for the total ===")

    def rmse_ou(total):
        rmse = np.sqrt(((total - df.actual_total) ** 2).mean())
        w, l, p = grade(total - df.line_total, df.tresid, 1.0)
        return rmse, w, l, p

    variants = {
        "current (mean pace)": df.exp_plays,
        "constant 72": pd.Series(72.0, index=df.index),
        "shrink50 toward 72": 72 + 0.5 * (df.exp_plays - 72),
        "geometric mean pace": np.sqrt(df.pace_home * df.pace_away),
        "min pace (slow team)": df[["pace_home", "pace_away"]].min(axis=1),
        "harmonic mean pace": 2 / (1 / df.pace_home + 1 / df.pace_away),
    }
    for name, plays in variants.items():
        total = df.ppa_sum * plays + df.epa_const
        rmse, w, l, p = rmse_ou(total)
        print(f"  {name:<24} RMSE {rmse:.2f}  OU {w}-{l}-{p} {fmt_pct(pct(w, l))}")
    print("  walk-forward pace coefficient b: P' = 72 + b*(P-72), fit on "
          "prior seasons:")
    grid = [0, 0.25, 0.5, 0.75, 1.0, 1.25]
    imp = 0
    for s in sorted(df.season.unique()):
        if s == df.season.min():
            continue
        hist, d = df[df.season < s], df[df.season == s]

        def h_rmse(b):
            t = hist.ppa_sum * (72 + b * (hist.exp_plays - 72)) + hist.epa_const
            return np.sqrt(((t - hist.actual_total) ** 2).mean())

        b = min(grid, key=h_rmse)
        t = d.ppa_sum * (72 + b * (d.exp_plays - 72)) + d.epa_const
        r0 = np.sqrt(((d.our_total - d.actual_total) ** 2).mean())
        r1 = np.sqrt(((t - d.actual_total) ** 2).mean())
        imp += r1 < r0
        print(f"  {s}: b*={b}  RMSE {r0:.2f}->{r1:.2f}")
    print(f"  WF pace coefficient improved RMSE in {imp} seasons")


def main():
    b = load("B")
    b8 = load("B8")
    test = b[b.season.isin(TEST_SEASONS)].copy()
    test8 = b8[b8.season.isin(TEST_SEASONS)].copy()
    season_table(test, "frame B")
    h_s1(test)
    h_s2(test)
    h_s3(test, test8)
    h_s4(test)
    totals_baseline(test)
    h_t4(test)
    h_t3(test)
    h_t1(test)
    s26 = b[b.season == 2026]
    print(f"\n=== 2026 harness slice (NOT published picks; n={len(s26)}) ===")
    w, l, p = grade(s26.spread_edge, s26.mresid, 0.5)
    ow, ol, op = grade(s26.total_edge, s26.tresid, 1.0)
    print(f"  ATS {w}-{l}-{p} {fmt_pct(pct(w, l))}   OU {ow}-{ol}-{op} "
          f"{fmt_pct(pct(ow, ol))}   model bias "
          f"{(s26.our_total - s26.actual_total).mean():+.2f} vs line "
          f"{(s26.line_total - s26.actual_total).mean():+.2f}")


if __name__ == "__main__":
    main()
