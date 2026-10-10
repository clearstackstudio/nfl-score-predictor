import type { Metadata } from "next";
import Link from "next/link";
import index from "../../data/recaps/index.json";

export const metadata: Metadata = {
  title: "Weekly recaps",
  description:
    "What the Honest Line model's picks got right and wrong, every week. No spin, no excuses — including the bad weeks.",
  alternates: { canonical: "/recaps" },
};

type RecapEntry = {
  id: string;
  title: string;
  period_label: string;
  published: string;
};

function fmtRecord(rec: number[]) {
  return `${rec[0]}-${rec[1]}` + (rec[2] ? `-${rec[2]}` : "");
}

export default function RecapsIndex() {
  const recaps = (index as { recaps: RecapEntry[] }).recaps ?? [];
  return (
    <div>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        Every week · wins and losses
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Weekly <span className="text-amber-400 light:text-amber-600">recaps</span>
      </h1>
      <p className="mt-4 max-w-2xl text-sm text-zinc-400 light:text-zinc-600">
        What the model&apos;s picks got right, what they got wrong, and one honest
        observation — published every Monday. A tout site would bury the bad weeks.
        We put them at the top of the page.
      </p>

      {recaps.length === 0 ? (
        <p className="mt-8 text-sm text-zinc-500">No recaps yet. Check back Monday.</p>
      ) : (
        <div className="mt-8 space-y-4">
          {recaps.map((r) => (
            <Link
              key={r.id}
              href={`/recaps/${r.id}`}
              className="block rounded-xl border border-white/10 bg-zinc-900/50 p-5 transition hover:border-amber-400/40 hover:bg-zinc-900 light:border-zinc-200 light:bg-white light:hover:border-amber-600/40"
            >
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">
                {r.period_label}
              </div>
              <div className="mt-1 font-display text-2xl font-semibold uppercase tracking-wide">
                {r.title}
              </div>
              <div className="mt-1 text-sm text-zinc-400 light:text-zinc-600">
                Published {r.published}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
