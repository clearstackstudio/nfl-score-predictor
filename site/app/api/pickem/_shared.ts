/** Server-side shared helpers for the pick'em leaderboard API routes.
 *  Storage: Vercel Blob, one file per entry:
 *    pickem/{sport}/{season}/{period}/{slug}.json
 *  Overwriting a file = updating that name's entry (one entry per name per period).
 */
import { head, list, put } from "@vercel/blob";

import nflPicks from "../../../data/picks.json";
import cfbPicks from "../../../data/cfb_picks.json";
import nbaPicks from "../../../data/nba_picks.json";
import ncaabPicks from "../../../data/ncaab_picks.json";

export type Sport = "nfl" | "cfb" | "nba" | "ncaab";
export const SPORTS: Sport[] = ["nfl", "cfb", "nba", "ncaab"];

type SlateGame = {
  away_abbr: string;
  home_abbr: string;
  gameday: string;
  line_spread: number;
  result?: { home_score: number; away_score: number } | null;
};

type Slate = {
  sport: Sport;
  season: string;
  period: string; // week number (nfl/cfb) or date (nba/ncaab)
  periodLabel: string;
  games: SlateGame[];
};

function toSlate(sport: Sport, raw: any): Slate | null {
  const picks = (raw?.picks ?? []) as any[];
  if (!picks.length) return null;
  const season = String(raw.season ?? "");
  const period =
    sport === "nfl" || sport === "cfb"
      ? String(raw.week ?? "")
      : String(raw.date ?? "");
  if (!period) return null;
  const games: SlateGame[] = picks.map((p) => ({
    away_abbr: String(p.away_abbr),
    home_abbr: String(p.home_abbr),
    gameday: String(p.gameday ?? ""),
    line_spread: Number(p.line_spread ?? 0),
    result: p.result
      ? {
          home_score: Number(p.result.home_score),
          away_score: Number(p.result.away_score),
        }
      : null,
  }));
  return {
    sport,
    season,
    period,
    periodLabel:
      sport === "nfl" || sport === "cfb" ? `Week ${period}` : period,
    games,
  };
}

export function getSlate(sport: Sport): Slate | null {
  switch (sport) {
    case "nfl":
      return toSlate(sport, nflPicks);
    case "cfb":
      return toSlate(sport, cfbPicks);
    case "nba":
      return toSlate(sport, nbaPicks);
    case "ncaab":
      return toSlate(sport, ncaabPicks);
  }
}

export function gameKey(g: { away_abbr: string; home_abbr: string }) {
  return `${g.away_abbr}@${g.home_abbr}`;
}

/** Display name -> filename slug. Strict charset so it doubles as path safety. */
export function slugify(name: string): string | null {
  const s = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9 _-]/g, "")
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 20);
  if (s.length < 2) return null;
  return s;
}

export function blobAvailable(): boolean {
  return !!process.env.BLOB_READ_WRITE_TOKEN;
}

function entryPath(sport: Sport, season: string, period: string, slug: string) {
  // encodeURIComponent on period (dates contain no slashes, but be safe)
  return `pickem/${sport}/${season}/${encodeURIComponent(period)}/${slug}.json`;
}

function periodPrefix(sport: Sport, season: string, period: string) {
  return `pickem/${sport}/${season}/${encodeURIComponent(period)}/`;
}

export type Entry = {
  name: string;
  picks: Record<string, "home" | "away">;
  updatedAt: string;
};

export async function readEntry(
  sport: Sport,
  season: string,
  period: string,
  slug: string
): Promise<Entry | null> {
  try {
    const meta = await head(entryPath(sport, season, period, slug));
    const res = await fetch(meta.url, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as Entry;
  } catch {
    return null;
  }
}

export async function writeEntry(
  sport: Sport,
  season: string,
  period: string,
  slug: string,
  entry: Entry
): Promise<void> {
  await put(entryPath(sport, season, period, slug), JSON.stringify(entry), {
    access: "public",
    addRandomSuffix: false,
    contentType: "application/json",
    cacheControlMaxAge: 0,
  });
}

export async function listEntryUrls(
  sport: Sport,
  season: string,
  period: string
): Promise<string[]> {
  const urls: string[] = [];
  let cursor: string | undefined;
  do {
    const page = await list({
      prefix: periodPrefix(sport, season, period),
      cursor,
      limit: 500,
    });
    for (const b of page.blobs) urls.push(b.url);
    cursor = page.cursor;
  } while (cursor);
  return urls;
}

/** Grade one entry's ATS picks against the slate's results. */
export function gradeEntry(
  slate: Slate,
  picks: Record<string, "home" | "away">
): { w: number; l: number; p: number } {
  let w = 0,
    l = 0,
    p = 0;
  const byKey = new Map(slate.games.map((g) => [gameKey(g), g]));
  for (const [k, side] of Object.entries(picks)) {
    const g = byKey.get(k);
    if (!g?.result) continue;
    const cover =
      g.result.home_score - g.result.away_score - g.line_spread;
    if (Math.abs(cover) < 0.01) {
      p++;
    } else if ((cover > 0) === (side === "home")) {
      w++;
    } else {
      l++;
    }
  }
  return { w, l, p };
}

/** Lockout: no submissions once the earliest gameday has begun (PT). */
export function isLocked(slate: Slate): boolean {
  const days = slate.games
    .map((g) => g.gameday)
    .filter(Boolean)
    .sort();
  if (!days.length) return false;
  // Earliest gameday at 00:00 America/Los_Angeles. Compare via date strings in PT.
  const nowPt = new Date(
    new Date().toLocaleString("en-US", { timeZone: "America/Los_Angeles" })
  );
  const pad = (n: number) => String(n).padStart(2, "0");
  const todayPt = `${nowPt.getFullYear()}-${pad(nowPt.getMonth() + 1)}-${pad(
    nowPt.getDate()
  )}`;
  return days[0] <= todayPt;
}

// ---- best-effort per-IP rate limiting (per serverless instance) ----
const hits = new Map<string, number[]>();
export function rateLimited(ip: string, limit = 12, windowMs = 3600_000): boolean {
  const now = Date.now();
  const arr = (hits.get(ip) ?? []).filter((t) => now - t < windowMs);
  arr.push(now);
  hits.set(ip, arr);
  return arr.length > limit;
}

export function clientIp(req: Request): string {
  return (
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    req.headers.get("x-real-ip") ||
    "unknown"
  );
}
