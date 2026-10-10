import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import index from "../../../data/recaps/index.json";

export async function generateStaticParams() {
  const recaps = (index as { recaps: { id: string }[] }).recaps ?? [];
  return recaps.map((r) => ({ id: r.id }));
}

type Recap = {
  id: string;
  title: string;
  period_label: string;
  published: string;
  overall: { ats: number[]; ou: number[] };
  sports: {
    sport: string;
    label: string;
    period: string;
    ats: number[];
    ou: number[];
    n_picks: number;
  }[];
  best_call: {
    label: string;
    kind: string;
    edge: number;
    prob: number;
    game: string;
    score: string;
    sport: string;
    period: string;
  } | null;
  worst_miss: {
    label: string;
    kind: string;
    edge: number;
    prob: number;
    game: string;
    score: string;
    sport: string;
    period: string;
  } | null;
  observation: string;
};

async function loadRecap(id: string): Promise<Recap | null> {
  try {
    const mod = await import(`../../../data/recaps/${id}.json`);
    return (mod.default ?? mod) as Recap;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const r = await loadRecap(id);
  if (!r) return { title: "Recap not found" };
  return {
    title: r.title,
    description: r.observation,
    alternates: { canonical: `/recaps/${id}` },
  };
}

function fmtRecord(rec: number[]) {
  return `${rec[0]}-${rec[1]}` + (rec[2] ? `-${rec[2]}` : "");
}

function winPct(rec: number[]) {
  return rec[0] + rec[1] === 0 ? "—" : `${Math.round((rec[0] / (rec[0] + rec[1])) * 100)}%`;
}

export default async function RecapPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const r = await loadRecap(id);
  if (!r) notFound();

  return (
    <div>
      <Link
        href="/recaps"
        className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 hover:text-amber-300 light:text-amber-700 light:hover:text-amber-600"
      >
        ← All recaps
      </Link>
      <div className="mt-4 flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        {r.period_label}
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        {r.title}
      </h1>
      <p className="mt-2 text-sm text-zinc-500">Published {r.published}</p>

      <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: "ATS", value: `${fmtRecord(r.overall.ats)} · ${winPct(r.overall.ats)}` },
          { label: "Totals", value: `${fmtRecord(r.overall.ou)} · ${winPct(r.overall.ou)}` },
        ].map((c) => (
          <div
            key={c.label}
            className="rounded-xl border border-white/10 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white"
          >
            <div className="tnum text-2xl font-extrabold">{c.value}</div>
            <div className="mt-1 text-xs text-zinc-500">Overall {c.label}</div>
          </div>
        ))}
      </div>

      <h2 className="mt-10 font-display text-3xl font-semibold uppercase tracking-wide">
        By sport
      </h2>
      <div className="mt-4 space-y-3">
        {r.sports.map((s) => (
          <div
            key={s.sport}
            className="rounded-xl border border-white/10 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div className="font-display text-xl font-semibold uppercase tracking-wide">
                {s.label} <span className="text-zinc-500">{s.period}</span>
              </div>
              <div className="tnum text-sm text-zinc-400 light:text-zinc-600">
                ATS {fmtRecord(s.ats)} · Totals {fmtRecord(s.ou)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {(r.best_call || r.worst_miss) && (
        <>
          <h2 className="mt-10 font-display text-3xl font-semibold uppercase tracking-wide">
            Calls
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {r.best_call && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/30 p-5 light:border-emerald-600/30 light:bg-emerald-50">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-400 light:text-emerald-700">
                  Best call
                </div>
                <div className="mt-2 font-display text-2xl font-semibold">
                  {r.best_call.label}
                </div>
                <div className="mt-1 text-sm text-zinc-400 light:text-zinc-600">
                  {r.best_call.game} · {r.best_call.score} · {r.best_call.sport}{" "}
                  {r.best_call.period}
                </div>
              </div>
            )}
            {r.worst_miss && (
              <div className="rounded-xl border border-red-500/30 bg-red-950/30 p-5 light:border-red-600/30 light:bg-red-50">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-red-400 light:text-red-700">
                  Worst miss
                </div>
                <div className="mt-2 font-display text-2xl font-semibold">
                  {r.worst_miss.label}
                </div>
                <div className="mt-1 text-sm text-zinc-400 light:text-zinc-600">
                  {r.worst_miss.game} · {r.worst_miss.score} — published at{" "}
                  {Math.round(r.worst_miss.prob * 100)}% and lost.
                </div>
              </div>
            )}
          </div>
        </>
      )}

      <h2 className="mt-10 font-display text-3xl font-semibold uppercase tracking-wide">
        The honest take
      </h2>
      <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
        {r.observation}
      </p>

      <p className="mt-8 max-w-2xl text-xs text-zinc-500">
        Every pick above was published before kickoff and graded against the final
        score. Nothing rewritten, nothing hidden — the full record lives on the{" "}
        <Link href="/track-record" className="underline hover:text-zinc-300">
          track record
        </Link>{" "}
        page.
      </p>
    </div>
  );
}
