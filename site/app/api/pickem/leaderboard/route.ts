import { NextResponse } from "next/server";
import {
  SPORTS,
  blobAvailable,
  getSlate,
  gradeEntry,
  isLocked,
  listEntryUrls,
  type Entry,
  type Sport,
} from "../_shared";

export const runtime = "nodejs";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const sport = url.searchParams.get("sport") as Sport;
  if (!SPORTS.includes(sport)) {
    return NextResponse.json({ error: "Unknown sport." }, { status: 400 });
  }
  if (!blobAvailable()) {
    return NextResponse.json(
      { error: "Leaderboard is not configured yet.", configured: false },
      { status: 503 }
    );
  }

  const slate = getSlate(sport);
  if (!slate) {
    return NextResponse.json(
      { error: "No active slate for this sport right now." },
      { status: 404 }
    );
  }

  const urls = await listEntryUrls(slate.sport, slate.season, slate.period);
  const rows: {
    name: string;
    w: number;
    l: number;
    p: number;
    winPct: number | null;
  }[] = [];

  // Fetch entries in small batches to bound concurrency.
  for (let i = 0; i < urls.length; i += 20) {
    const batch = await Promise.all(
      urls.slice(i, i + 20).map(async (u) => {
        try {
          const r = await fetch(u, { cache: "no-store" });
          if (!r.ok) return null;
          return (await r.json()) as Entry;
        } catch {
          return null;
        }
      })
    );
    for (const e of batch) {
      if (!e || !e.picks) continue;
      const { w, l, p } = gradeEntry(slate, e.picks);
      const decided = w + l;
      rows.push({
        name: String(e.name ?? "?").slice(0, 20),
        w,
        l,
        p,
        winPct: decided ? w / decided : null,
      });
    }
  }

  rows.sort(
    (a, b) => b.w - a.w || (b.winPct ?? 0) - (a.winPct ?? 0) || a.name.localeCompare(b.name)
  );

  return NextResponse.json(
    {
      configured: true,
      sport,
      season: slate.season,
      period: slate.period,
      periodLabel: slate.periodLabel,
      locked: isLocked(slate),
      count: rows.length,
      entries: rows.map((r, i) => ({ rank: i + 1, ...r })),
    },
    { headers: { "Cache-Control": "s-maxage=60, stale-while-revalidate=120" } }
  );
}
