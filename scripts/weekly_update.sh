#!/bin/bash
# Weekly NFL picks pipeline: grade the finished week, generate next week's picks,
# commit the updated site data, push. Vercel rebuilds the site from the push.
set -euo pipefail
cd "$HOME/workspace/nfl-score-predictor"

# The venv has pyarrow/pandas for parquet reads; /usr/bin/python3 does not.
PY="$HOME/workspace/nfl-score-predictor/.venv-cfb/bin/python"

# Label/unit tests first: fail the whole run before anything publishes.
$PY src/test_picks.py

$PY src/grade_week.py

GIT_ID="-c user.name=clearstackstudio -c user.email=334314751+clearstackstudio@users.noreply.github.com"
git $GIT_ID add site/data/picks.json "site/data/season_2026.json"

if git diff --cached --quiet; then
  echo "weekly_update: no changes to commit"
  exit 0
fi

WEEK=$($PY -c "import json; print(json.load(open('site/data/picks.json'))['week'])")
git $GIT_ID commit -m "Weekly update $(date +%F): graded prior week, picks for week $WEEK live"
git push origin main
echo "weekly_update: pushed"
