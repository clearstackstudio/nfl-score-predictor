# MLB Data Sources — Research Report (Phase 1, MLB expansion)

**Bottom line:** Baseball is in better shape than basketball. The paid option is cheaper (**$69** one-time vs $89 for NBA), and — unlike NBA — there is a *plausible free* closing-lines dataset (2021–2025, per-book open+close) plus **free historical starting-pitcher data from the official MLB API** (verified working today). The honest backtest is achievable; the only real decision is paid-clean vs free-with-caveats.

## 1. Closing lines (moneyline + total + run line) — the critical piece

### Tier A — Recommended (paid, clean)

**A1: Scottfree Analytics — MLB Historical Odds CSV — $69 one-time (sale, reg $99)**
- https://shop.scottfreellc.com/shop/p/mlb-historical-odds-data
- 28,613 MLB game rows (~12 seasons), same 146-column schema as their NBA product
- **Closing moneyline, run line (−1.5), and over/under**, plus opening lines where available
- Season, game date, scheduled ET, teams, final scores, ML target variables, ATS history fields, schema docs
- Dataset refreshes available to prior customers (same $19/mo-style refresh program as NBA)
- ⚠️ Verify at purchase that the snapshot includes the 2025 season (~12 seasons back from 2025 ≈ 2014–2025)

**A2: ArnavSaraogi/mlb-odds-scraper — FREE 76MB JSON release (with caveats)**
- https://github.com/ArnavSaraogi/mlb-odds-scraper (8 stars, 8 commits, created Aug 2025)
- **2021-03-20 → 2025-08-16**, per-book **opening + closing** moneyline, run line, and totals (FanDuel, DraftKings, BetMGM, Caesars, Bet365, BetRivers) **plus final scores** — exactly the fields a backtest needs
- Scraped from SportsBookReview; README notes SBR historical odds are reliable back to 2019-05-03
- ⚠️ **No license on the repo** — legally gray for reuse in a commercial-adjacent product. 4.5 seasons only (no 2015–2020). Small-maintainer risk (could vanish).
- Verdict: usable as a free cross-check / gap-filler, but the $69 CSV should be the primary source if Bryant approves the spend.

### Tier B — Usable with caveats

- **ParlayAPI historical ($19/mo × 1 month)** — `baseball_mlb` has 27,648 `sbr_close` matches, but coverage is **2010-04-04 → 2021-11-02**: missing 2022–2026 (4+ seasons). Worse than their NBA offering. Not recommended as primary.
- **the-odds-api.com** — free tier (500 credits/mo) has **no historical odds** (confirmed in a third-party project's docs); paid historical exists but is priced for ongoing use, not one-time backfill. Best role: **live daily lines for the site** once launched (same as the NBA plan).
- **Covers.com scrape** — has years of Pinnacle closers, but scraping it is ToS-gray and anti-bot-hardened. Not worth it with a $69 clean option on the table.

### Tier C — Rejected (dealbreakers)

- **Hugging Face**: zero MLB odds datasets (verified via API today).
- **Kaggle**: no current SBR/odds dump found (old links are dead or end ~2017).
- **DonBest / SportsDataIO / Covers paid**: all 5–15× the Scottfree price.
- **ESPN / MLB official**: no historical odds, ever (same as NBA).

## 2. Game results — easy, free

- **MLB Stats API** (`https://statsapi.mlb.com`, no key, unofficial-but-tolerated): schedules + scores back to 1901+. One call per date: `/api/v1/schedule?sportId=1&date=YYYY-MM-DD`.
- **pybaseball** (`pip install pybaseball`): schedule/results helpers; also Lahman/Chadwick and Retrosheet (play-by-play back to 1916) if ever needed.

## 3. Team + pitcher stats — free, and starting pitchers are available

This is the big structural difference vs. the NBA research: **the starting pitcher — the single most important input to an MLB model — is available historically for free.**

- **Historical starting pitchers (VERIFIED TODAY):** MLB Stats API schedule endpoint with `?hydrate=probablePitcher` returns the probable/actual starter for each side on historical dates (tested 2024-06-15: returned both starters). A full-season pull is one request per date (~180 dates/season). No key, no auth.
- **Pitcher/batter season stats:** pybaseball `pitching_stats(start,end)` / `batting_stats(start,end)` (FanGraphs-sourced: ERA, xERA, K%, WAR, wOBA, barrels, etc.), `team_batting(year)`. Free. ⚠️ Note: pybaseball's Baseball-Reference scrapers have rotted (community forks exist); stick to the FanGraphs functions, which are the maintained path.
- **Statcast (2015+)**: pybaseball `statcast()` for pitch-level data if the model ever wants stuff like pitcher xwOBA-against or velocity trends. Optional for v1.
- **FanGraphs direct**: also scrapable, but pybaseball wraps it — no need to go direct.

**What this means for the model:** a credible v1 is team batting/pitching ratings + starting-pitcher adjustment + park factors + home edge, all from free sources. The lines are the only paid piece.

## Recommended stack

| Need | Source | Cost |
|---|---|---|
| Historical closing lines (backtest) | **Scottfree MLB CSV** | **$69 one-time** |
| *Free alternative* closing lines | ArnavSaraogi JSON release (2021–2025, no license — caveat) | $0 |
| Game results + starting pitchers | MLB Stats API | Free |
| Team/pitcher stats | pybaseball (FanGraphs) | Free |
| Live daily lines (site, once launched) | the-odds-api free tier | Free |

**Simplest path:** Scottfree $69 → lines + scores in one file, ~12 seasons of closing ML/RL/total. Pair with MLB Stats API (results + starters) and pybaseball (stats). the-odds-api free tier for live lines. **Total: $69.**

**Cheapest path:** ArnavSaraogi free JSON (2021–2025) + MLB Stats API + pybaseball → **$0**, but only 4.5 seasons of lines, no license, and a bus factor of one.

## Modeling notes for Phase 2 (not decisions, just flags)

1. **Moneyline framework needed.** Baseball is a moneyline sport; the site's spread/total pick'em apparatus doesn't directly port. Natural MLB picks: moneyline winner, run line (−1.5), total. This is real product work, not just data plumbing.
2. **Weather matters for totals.** Wind (Wrigley blowing out), temperature, humidity move MLB totals. Open-Meteo is free — same pipeline as the football weather work. Phase-2 modeling question, data is free.
3. **Park factors** are derivable from the free data (multi-year run scoring by park) — no purchase needed.
4. **Season timing is on our side.** The 2026 regular season is over (2026 World Series about to start / just played, per SBR). Next Opening Day is ~late March 2027 — the model can be built over the winter with zero time pressure, and the backtest is the whole product until then.
5. **Bullpen/rest** and umpire tendencies are phase-2+ refinements; the free data covers them if wanted later.

## Open questions for Phase 2

1. Approve $69 Scottfree MLB CSV (and confirm it includes 2025), or go the $0 ArnavSaraogi route?
2. Product call: moneyline-only picks to start, or ML + run line + total from day one?
3. Include postseason in the backtest (recommend yes, same as NFL/NBA plan)?
