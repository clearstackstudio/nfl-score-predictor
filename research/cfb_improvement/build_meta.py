"""Build game_meta.parquet from the raw CFBD game snapshots in the repo.

One row per game_id: seasonType, week (within season type), conferenceGame,
home/away conference and classification. The merged cfb_games.parquet kept
only the raw week number, which collides between regular season and
postseason; this restores the true week identity for grouping/slicing.
"""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
RAW = REPO / "data" / "cfb" / "raw"

rows = []
for path in sorted(RAW.glob("games_*.json")):
    for d in json.loads(path.read_text()):
        rows.append({
            "game_id": int(d["id"]),
            "season_type": d.get("seasonType"),
            "week_true": d.get("week"),
            "conf_game": bool(d.get("conferenceGame")),
            "home_conf": d.get("homeConference"),
            "away_conf": d.get("awayConference"),
            "home_class": d.get("homeClassification"),
            "away_class": d.get("awayClassification"),
        })
meta = pd.DataFrame(rows).drop_duplicates("game_id")
meta.to_parquet(HERE / "game_meta.parquet", index=False)
print(f"{len(meta)} games -> game_meta.parquet")
print(meta.groupby(["season_type"]).size())
print("conf_game share:", round(meta["conf_game"].mean(), 3))
