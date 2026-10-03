# NBA Data Sources — Research Report (Phase 1, NBA expansion)

**Date:** 2026-10-02
**Goal:** Identify sources for (1) game results, (2) historical *closing* spread/total lines 2015-16→present, (3) box-score/efficiency stats.
**Bottom line:** There is no good *free* source of historical NBA closing lines. The old free SBR archive is dead, but its data survives inside ParlayAPI, and a purpose-built $89 CSV (Scottfree) is the cleanest buy. Game results and stats are free and easy.

---

## 1. Closing lines (spread + total) — the critical piece

### Tier A — Recommended

**Option A1: Scottfree Analytics — NBA Historical Odds CSV — $89 one-time**
- https://shop.scottfreellc.com/ (product: "NBA Historical Odds and Lines Data in CSV Format", sale $89, reg $129)
- 24,284 NBA game rows (~18+ seasons), 146-column schema
- **Closing spread, moneyline, and over/under**; "Final Odds Recorded within One Hour before Game Time"
- Opening lines where available (live capture from April 2026; historical opening backfill in progress — closing lines are complete, which is what the backtest needs)
- Date, scheduled ET time, teams, final scores, ML target variables, ATS history fields
- Schema documentation included; **free $0 sample CSV** available to inspect before buying: https://shop.scottfreellc.com/shop/p/historical-odds-sample-data
- Optional $19/mo refresh subscription keeps it current (8 pulls/month)
- No API key, no rate limits, no scraping — just a CSV download. Closest thing to an "nflverse for NBA lines" that exists.
- ⚠️ Verify at purchase time that the snapshot includes the 2025-26 season (they sell "current product snapshots"; refresh sub covers ongoing).

**Option A2: ParlayAPI historical closing-odds — ~$19 for one month**
- https://parlay-api.com/historical-odds-api · docs: https://parlay-api.com/docs
- **Verified live 2026-10-02** via their free `/v1/historical/stats` endpoint: `basketball_nba` = 49,436 matches, earliest **2007-10-30**, latest **2023-01-16**
- Bookmakers include **`sbr_close`** (19,641 matches — this is the old SportsBookReview closing archive, resurrected) plus DraftKings/Caesars/BetMGM/FanDuel/Fanatics (~4k matches each, ~2022-23)
- Endpoint: `GET /v1/historical/sports/basketball_nba/closing-odds?date=YYYY-MM-DD&markets=h2h,spreads,totals` — **one call per date** (not per game), flat 10 credits/call
- Math: ~170 game-dates/season × 16 seasons ≈ 2,700 calls ≈ 27,000 credits → fits in **Starter $19/mo (100K credits)**; cancel after the pull
- Free tier: 1,000 credits/mo ≈ 100 date-pulls (their docs claim historical works on free; another source says free = 2-day history — verify before relying on free)
- ⚠️ **Gap: nothing after 2023-01-16.** Seasons 2023-24, 2024-25, 2025-26 need a second source (the-odds-api historical, or Scottfree refresh)
- Signup: free API key at parlay-api.com, no card required for free tier

### Tier B — Usable with caveats

**Option B1: the-odds-api.com historical — paid, 2020+ only**
- https://the-odds-api.com · historical snapshots from **June 2020** (10-min intervals), 5-min from Sept 2022
- Historical endpoint is **paid plans only**; costs 10 credits × regions × markets per timestamp (one US snapshot with h2h+spreads+totals = 30 credits)
- Free tier 500 credits/mo is for current odds, not historical
- **Dealbreaker for full history** (nothing before June 2020), but it's the best-priced way to **fill the 2023-2026 gap** left by ParlayAPI
- Good for the live site's *current* lines too (free tier covers daily odds pulls)

**Option B2: Kaggle `ehallmar/nba-historical-stats-and-betting-data` — free, stale**
- https://www.kaggle.com/datasets/ehallmar/nba-historical-stats-and-betting-data
- Multi-book (Pinnacle, 5Dimes, Bookmaker, BetOnline, Bovada…): `nba_betting_spread.csv`, `nba_betting_totals.csv`, `nba_betting_money_line.csv` + games/players tables
- ⚠️ **Updated 8 years ago — ends ~2017-18.** Covers 2015-16→2017-18 only. Unclear whether lines are open or close. Useful as a cross-check for the early window, not a primary source.

**Option B3: hoopR / ESPN odds — free, unreliable for backtest**
- hoopR's `load_nba_schedule()` (2002+) has **no odds columns** (verified in docs)
- ESPN's API embeds `game_spread` in play-by-play payloads, but only for recent seasons and it's a snapshot of unclear timing — not a documented closing line. Fine for spot checks, not the backtest.

### Tier C — Rejected

- **sportsbookreviewsonline.com archive (free xlsx, 2007-08→~2022-23, open+close+2H lines)** — **domain is dead** (404s verified 2026-10-02). Was the best free source; its data survives as ParlayAPI's `sbr_close`.
- **wippa-studios/wippa-nba-data (GitHub)** — README claims closing spread/total 2016-2026, but the actual scraper (`scripts/scrape_oddsportal.py`) only extracts **moneyline odds** from OddsPortal page text. 1 star, 5 commits, created Sept 2026. **Do not trust the spread/total columns.**
- **OddsPortal direct scraping** — has historical open/close per book, but scraping violates ToS and it's Cloudflare-hardened. Not worth it.
- **Covers.com** — quoted $1,000/season (via SportsDirect) historically. Absurd pricing.
- **DonBest** — has Opening/Closing Lines archives back to ~2003, but requires $650/6mo Gold subscription (one lifetime free trial). Overkill when $89 buys a CSV.
- **SportsDataIO** — has historical odds API but starts ~$100+/mo; no advantage over the options above.

---

## 2. Game results (date, teams, scores) — easy, free

Any of these works; they agree with each other:

1. **hoopR / sportsdataverse-data** (R package, but CSVs downloadable directly): `load_nba_schedule()` 2002→present, per-game scores, dates, venues. Release assets: https://github.com/sportsdataverse/sportsdataverse-data
2. **nba_api** (Python, `pip install nba_api`): `LeagueGameFinder` — official stats.nba.com data. Free, no key. Courtesy rate limit ~1 req/sec.
3. **basketball-reference.com**: schedule pages per season/month. Scrapable with 3-sec delays; no key. (No odds on bball-ref — scores only.)
4. Kaggle `nathanlauga/nba-games` — static CSV, fine but frozen in time.

**Recommendation:** nba_api (`LeagueGameFinder`) or hoopR schedule CSVs — both free, complete, and current.

---

## 3. Efficiency stats (ORtg/DRtg/pace) — easy, free

Per-game team box scores are sufficient to compute possessions, offensive/defensive rating, and pace:

1. **nba_api** — `BoxScoreTraditionalV2` (per-game team + player box scores), `LeagueDashTeamStats` (season aggregates incl. pace, ORtg/DRtg). Free, no key. This is the primary stats source.
2. **basketball-reference.com** — team per-game + advanced tables (pace, ORtg, DRtg) back to 1970s. Good cross-check.
3. **hoopR** — `load_nba_team_box()` 2002+, hosted CSVs. Same underlying ESPN/stats data, convenient bulk download.

Possessions can be estimated from box scores the standard way (FGA − ORB + TOV + 0.44×FTA); no tracking data needed for v1.

---

## Recommended stack

| Need | Source | Cost | Signup |
|---|---|---|---|
| Historical closing spread + total (backtest) | **Scottfree NBA CSV** ($89 one-time) | $89 | None — direct download; inspect free sample first |
| *Alternative* historical lines | ParlayAPI Starter, one month, pull `sbr_close` 2007→2023 | $19 | Free API key at parlay-api.com |
| Fill 2023-24→present lines gap (if ParlayAPI route) | the-odds-api historical (paid) | ~$30-60 one-time pull | API key at the-odds-api.com |
| Game results | nba_api `LeagueGameFinder` or hoopR schedule CSVs | Free | None |
| Box-score / efficiency stats | nba_api (`BoxScoreTraditionalV2`, `LeagueDashTeamStats`) | Free | None |
| Live current lines (site) | the-odds-api free tier (500 credits/mo) | Free | API key at the-odds-api.com |

**Simplest path:** buy the Scottfree NBA CSV ($89) → lines + scores in one file, back to ~2007, closing lines recorded within an hour of tip. Pair with nba_api for box scores. Use the-odds-api free tier for the live site's daily lines. Total data cost: $89 + $0.

**Cheapest path:** ParlayAPI Starter $19 × 1 month → pull all `sbr_close` closing lines 2007-01-2023; the-odds-api paid pull for 2023→present; nba_api for scores/stats. Total: ~$50-80 but more moving parts and two sources to reconcile.

## Open questions for Phase 2
1. Confirm Scottfree's current snapshot includes 2025-26 (or plan the $19/mo refresh).
2. Decide spread-vs-moneyline framing for the pick'em game (NBA is a spread+total sport like the NFL — the existing framework ports cleanly; moneyline can come later).
3. Playoff/Play-in handling: lines files include playoffs; decide whether the model covers them (recommend yes — same as NFL).
