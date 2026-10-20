"""Market evaluation: model vs consensus closing lines, 2025-26 only.

Free odds source: Shane's NHL spreadsheet (shanemcd.org) — consensus
moneyline/total for all 1,312 games of 2025-26, the only season his
files carry odds for. The model was fitted (discovery 2019-2022)
without any odds, so this is a clean out-of-sample market check on a
validation season. Lines are a multi-site consensus, not a single
sharp book — stated wherever these numbers are published.

Reads data/nhl/backtest_predictions.parquet (season 2025 rows) and
data/nhl/shane_odds_2025.csv. Writes data/nhl/market_eval.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ratings import total_probs  # noqa: E402

DATA = Path(__file__).resolve().parents[2] / "data" / "nhl"

NAME_TO_ABBR = {
    "Anaheim Ducks": "ANA", "Boston Bruins": "BOS", "Buffalo Sabres": "BUF",
    "Calgary Flames": "CGY", "Carolina Hurricanes": "CAR",
    "Chicago Blackhawks": "CHI", "Colorado Avalanche": "COL",
    "Columbus Blue Jackets": "CBJ", "Dallas Stars": "DAL",
    "Detroit Red Wings": "DET", "Edmonton Oilers": "EDM",
    "Florida Panthers": "FLA", "Los Angeles Kings": "LAK",
    "Minnesota Wild": "MIN", "Montreal Canadiens": "MTL",
    "Nashville Predators": "NSH", "New Jersey Devils": "NJD",
    "New York Islanders": "NYI", "New York Rangers": "NYR",
    "Ottawa Senators": "OTT", "Philadelphia Flyers": "PHI",
    "Pittsburgh Penguins": "PIT", "San Jose Sharks": "SJS",
    "Seattle Kraken": "SEA", "St. Louis Blues": "STL",
    "Tampa Bay Lightning": "TBL", "Toronto Maple Leafs": "TOR",
    "Utah Mammoth": "UTA", "Vancouver Canucks": "VAN",
    "Vegas Golden Knights": "VGK", "Washington Capitals": "WSH",
    "Winnipeg Jets": "WPG",
}


def implied(american: float) -> float:
    a = float(american)
    return (-a) / (-a + 100) if a < 0 else 100 / (a + 100)


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def logloss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def main() -> None:
    pred = pd.read_parquet(DATA / "backtest_predictions.parquet")
    pred = pred[pred["season"] == 2025].copy()
    pred["date"] = pd.to_datetime(pred["date"]).dt.date.astype(str)

    raw_cols = [c.strip() for c in
                pd.read_csv(DATA / "shane_odds_2025.csv", nrows=0).columns]
    assert len(raw_cols) == 18, f"unexpected Shane columns: {raw_cols}"
    odds = pd.read_csv(DATA / "shane_odds_2025.csv", header=0,
                       names=["date", "t_sask", "t_et", "away_name",
                              "away_score", "home_name", "home_score",
                              "status", "away_goalie", "home_goalie",
                              "ou_line", "over_price", "under_price",
                              "away_ml", "home_ml", "pl_spread",
                              "pl_away", "pl_home"], skiprows=1)
    odds["home"] = odds["home_name"].map(NAME_TO_ABBR)
    odds["away"] = odds["away_name"].map(NAME_TO_ABBR)
    odds = odds.dropna(subset=["home", "away", "home_ml", "away_ml"])

    m = pred.merge(odds, on=["date", "home", "away"], how="inner")
    print(f"joined games: {len(m)} of {len(pred)} predictions")
    y = m["home_win"].to_numpy()

    # de-vigged market probabilities
    ph = np.array([implied(v) for v in m["home_ml"]])
    pa = np.array([implied(v) for v in m["away_ml"]])
    mkt = ph / (ph + pa)

    out = {
        "games": int(len(m)),
        "model_brier": round(brier(m["p_home"].to_numpy(), y), 4),
        "market_brier": round(brier(mkt, y), 4),
        "model_logloss": round(logloss(m["p_home"].to_numpy(), y), 4),
        "market_logloss": round(logloss(mkt, y), 4),
        "model_su_acc": round(float(np.mean((m["p_home"] > 0.5) == (y == 1))), 4),
        "market_su_acc": round(float(np.mean((mkt > 0.5) == (y == 1))), 4),
    }

    # totals: model lambda-sum vs the closing total line
    tot_act = (m["home_goals"] + m["away_goals"]).to_numpy(dtype=float)
    tot_model = (m["lam_h"] + m["lam_a"]).to_numpy()
    line = m["ou_line"].to_numpy(dtype=float)
    out["model_total_rmse"] = round(float(np.sqrt(np.mean((tot_model - tot_act) ** 2))), 3)
    out["line_total_rmse"] = round(float(np.sqrt(np.mean((line - tot_act) ** 2))), 3)

    # O/U at the pre-registered publishing threshold: |edge| >= 0.5 goals
    picks = []
    for r in m.itertuples():
        edge = (r.lam_h + r.lam_a) - r.ou_line
        if abs(edge) < 0.5:
            continue
        actual = r.home_goals + r.away_goals
        if actual == r.ou_line:
            res = "push"
        elif (actual > r.ou_line) == (edge > 0):
            res = "win"
        else:
            res = "loss"
        picks.append(res)
    if picks:
        w, l, pu = picks.count("win"), picks.count("loss"), picks.count("push")
        out["ou_at_0.5"] = {"plays": len(picks), "record": f"{w}-{l}-{pu}",
                            "win_pct": round(w / max(w + l, 1), 4)}

    # moneyline disagreement subset (informational): |model - market| >= 5pp
    dis = np.abs(m["p_home"].to_numpy() - mkt) >= 0.05
    if dis.sum():
        side_home = m["p_home"].to_numpy()[dis] > mkt[dis]
        won = np.where(side_home, y[dis] == 1, y[dis] == 0)
        prices = np.where(side_home, m["home_ml"].to_numpy()[dis],
                          m["away_ml"].to_numpy()[dis])
        profit = np.where(won, np.where(prices > 0, prices, 10000 / -prices), -100.0)
        out["ml_disagree_5pp"] = {
            "plays": int(dis.sum()), "wins": int(won.sum()),
            "flat100_roi_pct": round(float(profit.sum()) / (100 * dis.sum()) * 100, 1),
        }

    (DATA / "market_eval.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
