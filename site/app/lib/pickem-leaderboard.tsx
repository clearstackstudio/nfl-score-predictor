"use client";

import { useCallback, useEffect, useState } from "react";

type Sport = "nfl" | "cfb" | "nba" | "ncaab";

type BoardEntry = {
  rank: number;
  name: string;
  w: number;
  l: number;
  p: number;
  winPct: number | null;
};

type BoardData = {
  configured: boolean;
  periodLabel: string;
  locked: boolean;
  count: number;
  entries: BoardEntry[];
};

type Stored = {
  weeks: Record<string, { ats?: Record<string, string> }>;
};

function pct(x: number | null): string {
  if (x == null) return "—";
  return `${Math.round(x * 100)}%`;
}

export default function PickemLeaderboard({
  sport,
  lsKey,
  periodKey,
  gameCount,
}: {
  sport: Sport;
  lsKey: string;
  periodKey: string;
  gameCount: number;
}) {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [myPicks, setMyPicks] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      const r = await fetch(`/api/pickem/leaderboard?sport=${sport}`, {
        cache: "no-store",
      });
      if (r.status === 503) {
        setBoard({ configured: false, periodLabel: "", locked: false, count: 0, entries: [] });
      } else if (r.ok) {
        setBoard(await r.json());
      }
    } catch {
      /* offline — leave the local game working */
    } finally {
      setLoading(false);
    }
  }, [sport]);

  useEffect(() => {
    load();
    try {
      const raw = localStorage.getItem(lsKey);
      if (raw) {
        const d = JSON.parse(raw) as Stored;
        setMyPicks(d.weeks?.[periodKey]?.ats ?? {});
      }
    } catch { /* ignore */ }
    try {
      const saved = localStorage.getItem("hl-pickem-name");
      if (saved) setName(saved);
    } catch { /* ignore */ }
  }, [load, lsKey, periodKey]);

  const pickedCount = Object.keys(myPicks).length;
  const complete = pickedCount >= gameCount && gameCount > 0;

  async function submit() {
    setMessage(null);
    const clean = name.trim();
    if (clean.length < 2 || clean.length > 20) {
      setMessage({ ok: false, text: "Display name needs 2–20 characters." });
      return;
    }
    if (!complete) {
      setMessage({ ok: false, text: `Pick all ${gameCount} games first — then join.` });
      return;
    }
    setSubmitting(true);
    try {
      const r = await fetch("/api/pickem/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sport, name: clean, picks: myPicks }),
      });
      const d = await r.json();
      if (r.ok) {
        setMessage({ ok: true, text: `You're on the board as “${d.name}”. Good luck.` });
        try {
          localStorage.setItem("hl-pickem-name", clean);
        } catch { /* ignore */ }
        load();
      } else {
        setMessage({ ok: false, text: d.error ?? "Submission failed." });
      }
    } catch {
      setMessage({ ok: false, text: "Network error — try again." });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-10">
      <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">
        Leaderboard{" "}
        <span className="font-sans text-sm font-medium normal-case tracking-normal text-zinc-500">
          · community pick&apos;em, spread picks
        </span>
      </h2>
      <p className="mt-1 max-w-2xl text-sm text-zinc-400 light:text-zinc-600">
        Display names only — no accounts, no emails. One card per name per{" "}
        {sport === "nfl" || sport === "cfb" ? "week" : "day"}; you can update it
        until games start.
      </p>

      {loading ? (
        <div className="mt-4 text-sm text-zinc-500">Loading standings…</div>
      ) : board && !board.configured ? (
        <div className="mt-4 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 text-sm text-zinc-400 light:border-zinc-200 light:bg-white light:text-zinc-600">
          The public leaderboard is coming soon — your card still saves in this
          browser and grades against the model.
        </div>
      ) : (
        <>
          {/* Submit row */}
          <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 sm:flex-row sm:items-center light:border-zinc-200 light:bg-white">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Display name"
              maxLength={20}
              className="w-full rounded-xl border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-amber-400 focus:outline-none sm:max-w-xs light:border-zinc-300 light:bg-zinc-50 light:text-zinc-900"
            />
            <button
              onClick={submit}
              disabled={submitting || !complete || board?.locked}
              className="rounded-xl bg-amber-400 px-5 py-2.5 text-sm font-bold uppercase tracking-wider text-zinc-950 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {submitting
                ? "Submitting…"
                : board?.locked
                  ? "Locked — games started"
                  : "Submit my card"}
            </button>
            <span className="text-xs text-zinc-500">
              {complete
                ? `${pickedCount} of ${gameCount} picked — ready`
                : `${pickedCount} of ${gameCount} picked`}
            </span>
          </div>
          {message && (
            <div
              className={`mt-3 rounded-xl px-4 py-2.5 text-sm font-medium ${
                message.ok
                  ? "bg-emerald-400/10 text-emerald-300 light:text-emerald-700"
                  : "bg-rose-400/10 text-rose-300 light:text-rose-700"
              }`}
            >
              {message.text}
            </div>
          )}

          {/* Standings */}
          <div className="mt-4 overflow-x-auto rounded-2xl border border-zinc-800 light:border-zinc-200">
            {board && board.entries.length > 0 ? (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-zinc-800 text-xs uppercase tracking-wider text-zinc-500 light:border-zinc-200 light:text-zinc-600">
                    <th className="px-4 py-3">#</th>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">W-L</th>
                    <th className="px-4 py-3">Win%</th>
                  </tr>
                </thead>
                <tbody>
                  {board.entries.map((e) => (
                    <tr
                      key={e.rank}
                      className="border-b border-zinc-800/60 last:border-0 light:border-zinc-200"
                    >
                      <td className="px-4 py-3 font-mono font-bold text-amber-300 light:text-amber-700">
                        {e.rank}
                      </td>
                      <td className="px-4 py-3 font-semibold">{e.name}</td>
                      <td className="px-4 py-3 font-mono">
                        {e.w}-{e.l}
                        {e.p ? `-${e.p}` : ""}
                      </td>
                      <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">
                        {pct(e.winPct)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-5 text-sm text-zinc-500">
                No cards submitted yet for {board?.periodLabel ?? "this period"} — be
                the first.
              </div>
            )}
          </div>
          {board && board.count > 0 && (
            <p className="mt-2 text-xs text-zinc-500">
              {board.count} {board.count === 1 ? "card" : "cards"} · {board.periodLabel} ·
              graded as games go final.
            </p>
          )}
        </>
      )}
    </div>
  );
}
