import { NextResponse } from "next/server";
import {
  SPORTS,
  blobAvailable,
  clientIp,
  gameKey,
  getSlate,
  isLocked,
  rateLimited,
  slugify,
  writeEntry,
  type Sport,
} from "../_shared";

export const runtime = "nodejs";

type Body = {
  sport?: string;
  name?: string;
  picks?: Record<string, string>;
};

export async function POST(req: Request) {
  if (!blobAvailable()) {
    return NextResponse.json(
      { error: "Leaderboard is not configured yet — please try again later." },
      { status: 503 }
    );
  }

  const ip = clientIp(req);
  if (rateLimited(ip)) {
    return NextResponse.json(
      { error: "Too many submissions — please slow down." },
      { status: 429 }
    );
  }

  let body: Body;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body." }, { status: 400 });
  }

  const sport = body.sport as Sport;
  if (!SPORTS.includes(sport)) {
    return NextResponse.json({ error: "Unknown sport." }, { status: 400 });
  }

  const slug = slugify(body.name ?? "");
  if (!slug) {
    return NextResponse.json(
      { error: "Pick a display name: 2–20 characters, letters and numbers." },
      { status: 400 }
    );
  }
  const name = (body.name ?? "").trim().slice(0, 20);

  const slate = getSlate(sport);
  if (!slate) {
    return NextResponse.json(
      { error: "No active slate for this sport right now." },
      { status: 400 }
    );
  }
  if (isLocked(slate)) {
    return NextResponse.json(
      { error: `This ${slate.periodLabel} card is locked — games have started.` },
      { status: 403 }
    );
  }

  // Validate: every game picked exactly once, values are home/away.
  const picks = body.picks ?? {};
  const validKeys = new Set(slate.games.map(gameKey));
  const clean: Record<string, "home" | "away"> = {};
  for (const g of slate.games) {
    const k = gameKey(g);
    const v = picks[k];
    if (v !== "home" && v !== "away") {
      return NextResponse.json(
        { error: `Pick every game to join the leaderboard (${slate.games.length} games).` },
        { status: 400 }
      );
    }
    clean[k] = v;
  }
  for (const k of Object.keys(picks)) {
    if (!validKeys.has(k)) {
      return NextResponse.json({ error: "Unknown game in picks." }, { status: 400 });
    }
  }

  const now = new Date().toISOString();
  await writeEntry(slate.sport, slate.season, slate.period, slug, {
    name,
    picks: clean,
    updatedAt: now,
  });

  return NextResponse.json({ ok: true, name, period: slate.periodLabel });
}
