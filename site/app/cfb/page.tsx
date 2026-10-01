import picksData from "../../data/cfb_picks.json";
import { fmtSpread, fmtPct, trim } from "../lib/format";
import CfbTeamLogo from "../lib/cfb-team-logo";

type Pick = {
  away: string; home: string; away_abbr: string; home_abbr: string;
  gameday: string; weekday: string; neutral?: boolean;
  line_spread: number; line_total: number;
  our_spread: number; our_total: number;
  spread_edge: number; total_edge: number;
  pick_spread: "home" | "away" | null;
  pick_total: "over" | "under" | null;
  pick_spread_label: string | null;
  pick_total_label: string | null;
  cover_prob: number | null; ou_prob: number | null;
};

type PicksFile = {
  sport: string; season: number; week: number | null;
  generated: string | null; disclaimer: string;
  pending?: boolean; pending_reason?: string;
  parlay?: Parlay | null; picks: Pick[];
};

const data = picksData as PicksFile;
const picks = data.picks;

function fmtGameday(p: Pick): string {
  if (p.neutral) return "Neutral site";
  if (!p.gameday) return "";
  const parts = p.gameday.split("-").map(Number);
  if (parts.length < 3) return p.gameday;
  const [, m, d] = parts;
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const wd = p.weekday ? p.weekday.slice(0, 3) + ", " : "";
  return `${wd}${months[m - 1]} ${d}`;
}

function spreadPickText(p: Pick): string {
  if (p.pick_spread_label) return `${p.pick_spread_label} · ${fmtPct(p.cover_prob)} to cover`;
  const team = p.pick_spread === "home" ? p.home : p.away;
  return `${team} · ${fmtPct(p.cover_prob)} to cover`;
}

function ouPickText(p: Pick): string {
  if (p.pick_total_label) return `${p.pick_total_label} · ${fmtPct(p.ou_prob)}`;
  return `${p.pick_total === "over" ? "Over" : "Under"} ${trim(p.line_total)} · ${fmtPct(p.ou_prob)}`;
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
      <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
      {children}
    </div>
  );
}

function MarketPanel({
  name, ourLabel, ourCaption, vegasLabel, vegasCaption, edge, edgeCaption, pick,
}: {
  name: string; ourLabel: string; ourCaption: string;
  vegasLabel: string; vegasCaption: string;
  edge: number; edgeCaption: string; pick: React.ReactNode;
}) {
  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-white/5 bg-zinc-950/70 light:border-zinc-200 light:bg-zinc-50">
      <div className="grid grid-cols-3 divide-x divide-white/5 light:divide-zinc-200">
        <div className="p-3.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{name} · us</div>
          <div className="tnum mt-1.5 font-mono text-[15px] font-semibold text-zinc-100 light:text-zinc-900">{ourLabel}</div>
          <div className="mt-0.5 text-[11px] text-zinc-600 light:text-zinc-500">{ourCaption}</div>
        </div>
        <div className="p-3.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{name} · Vegas</div>
          <div className="tnum mt-1.5 font-mono text-[15px] text-zinc-400 light:text-zinc-600">{vegasLabel}</div>
          <div className="mt-0.5 text-[11px] text-zinc-600 light:text-zinc-500">{vegasCaption}</div>
        </div>
        <div className="p-3.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Disagreement</div>
          <div className="tnum mt-1.5 font-mono text-[15px] text-zinc-400 light:text-zinc-600">{trim(Math.abs(edge))} pts</div>
          <div className="mt-0.5 text-[11px] text-zinc-600 light:text-zinc-500">{edgeCaption}</div>
        </div>
      </div>
      <div className="border-t border-white/5 light:border-zinc-200">{pick}</div>
    </div>
  );
}

function PickStrip({ active, children }: { active: boolean; children: React.ReactNode }) {
  if (active) {
    return (
      <div className="border-l-2 border-amber-400 bg-amber-400/[0.07] px-4 py-3">
        <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-amber-400/90 light:text-amber-700">Model pick</div>
        <div className="mt-0.5 text-[15px] font-semibold text-amber-100 light:text-amber-800">{children}</div>
      </div>
    );
  }
  return <div className="px-4 py-2.5 text-[13px] text-zinc-600 light:text-zinc-500">No play — we agree with Vegas here.</div>;
}

function GameCard({ p }: { p: Pick }) {
  return (
    <article className="rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/70 to-zinc-900/30 p-5 transition-colors hover:border-white/20 light:border-zinc-200 light:from-white light:to-zinc-50 light:hover:border-zinc-300">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex flex-wrap items-center gap-x-2.5 text-[17px] font-bold tracking-tight">
          <span className="inline-flex items-center gap-2">
            <CfbTeamLogo name={p.away} size={26} />{p.away}
          </span>
          <span className="text-sm font-medium text-zinc-600 light:text-zinc-400">@</span>
          <span className="inline-flex items-center gap-2">
            <CfbTeamLogo name={p.home} size={26} />{p.home}
          </span>
        </h2>
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs font-medium text-zinc-400 light:border-zinc-200 light:bg-zinc-100 light:text-zinc-600">
          {fmtGameday(p)}
        </span>
      </div>
      <MarketPanel
        name="Spread"
        ourLabel={fmtSpread(p.our_spread, p.home, p.away)}
        ourCaption="Our number"
        vegasLabel={fmtSpread(p.line_spread, p.home, p.away)}
        vegasCaption="Vegas line"
        edge={p.spread_edge}
        edgeCaption="pts of disagreement"
        pick={<PickStrip active={!!p.pick_spread}>{p.pick_spread ? spreadPickText(p) : null}</PickStrip>}
      />
      <MarketPanel
        name="Total"
        ourLabel={trim(p.our_total)}
        ourCaption="Our number"
        vegasLabel={trim(p.line_total)}
        vegasCaption="Vegas line"
        edge={p.total_edge}
        edgeCaption="pts of disagreement"
        pick={<PickStrip active={!!p.pick_total}>{p.pick_total ? ouPickText(p) : null}</PickStrip>}
      />
    </article>
  );
}

type ParlayLeg = { game: string; market: "spread" | "total"; label: string; prob: number };
type Parlay = { legs: ParlayLeg[]; combined_prob: number; fair_odds: string; book_pays: string } | null;

function ParlayCard({ parlay }: { parlay: Parlay }) {
  if (!parlay || parlay.legs.length < 2) return null;
  return (
    <section className="mb-8 overflow-hidden rounded-2xl border border-amber-400/25 bg-gradient-to-b from-amber-400/[0.09] to-amber-400/[0.03]">
      <div className="flex flex-wrap items-baseline justify-between gap-2 px-5 pt-5">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">For fun · not a strategy</div>
          <h2 className="mt-1 font-display text-3xl font-semibold uppercase tracking-wide">Parlay of the week</h2>
        </div>
        <span className="text-sm text-zinc-500">Our {parlay.legs.length} highest-conviction picks, combined</span>
      </div>
      <ul className="mt-4 space-y-2 px-5">
        {parlay.legs.map((l) => (
          <li key={`${l.game}-${l.market}`} className="flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-zinc-950/70 px-4 py-2.5 light:border-zinc-200 light:bg-white">
            <div>
              <span className="font-bold text-amber-200 light:text-amber-700">{l.label}</span>
              <span className="ml-2 text-sm text-zinc-500">{l.game}</span>
            </div>
            <span className="tnum font-mono text-sm font-semibold text-zinc-300 light:text-zinc-700">{fmtPct(l.prob)}</span>
          </li>
        ))}
      </ul>
      <div className="mt-4 grid grid-cols-2 gap-3 px-5">
        <div className="rounded-xl border border-white/5 bg-zinc-950/70 p-3.5 light:border-zinc-200 light:bg-white">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Model&rsquo;s combined chance</div>
          <div className="tnum mt-1 text-xl font-extrabold">{fmtPct(parlay.combined_prob)} <span className="text-sm font-semibold text-zinc-400 light:text-zinc-600">· fair odds {parlay.fair_odds}</span></div>
        </div>
        <div className="rounded-xl border border-white/5 bg-zinc-950/70 p-3.5 light:border-zinc-200 light:bg-white">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Books typically pay</div>
          <div className="tnum mt-1 text-xl font-extrabold">{parlay.book_pays} <span className="text-sm font-semibold text-zinc-400 light:text-zinc-600">on {parlay.legs.length} legs</span></div>
        </div>
      </div>
      <p className="px-5 pb-5 pt-4 text-[13px] leading-relaxed text-zinc-400 light:text-zinc-600">
        The honest fine print: parlays multiply the book&rsquo;s edge along with the payout. And our model&rsquo;s
        confidence is unproven until the backtest says otherwise. Entertainment, not a strategy.
      </p>
    </section>
  );
}

function PendingNotice() {
  return (
    <div className="rounded-2xl border border-amber-400/25 bg-amber-400/[0.06] p-8 text-center light:bg-amber-50">
      <div className="font-display text-2xl font-semibold uppercase tracking-wide">First kickoff soon</div>
      <p className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        {data.pending_reason} Check back soon — the pipeline, the model, and the backtest are all built.
        Only the data connection is missing.
      </p>
    </div>
  );
}

export default function CfbHome() {
  const nSpread = picks.filter((p) => p.pick_spread).length;
  const nTotal = picks.filter((p) => p.pick_total).length;

  return (
    <div>
      <div className="mb-8">
        <Eyebrow>
          College football · {data.season} season{data.week ? ` · Week ${data.week}` : ""}
          {data.generated ? ` · generated ${data.generated}` : ""}
        </Eyebrow>
        <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide sm:text-6xl">
          College <span className="text-amber-400 light:text-amber-600">picks</span>
        </h1>
        <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
          FBS games from opponent-adjusted PPA ratings — college football&rsquo;s answer to EPA,
          garbage time excluded. The model never sees the betting line; the line is only the
          benchmark we measure against. Same honesty rules as the NFL side: every pick published
          before kickoff, every result graded in public.
        </p>
        {data.pending || picks.length === 0 ? (
          <div className="mt-6"><PendingNotice /></div>
        ) : (
          <>
            <div className="mt-5 flex flex-wrap gap-x-8 gap-y-3">
              {[[String(picks.length), "games"], [String(nSpread), "spread plays"], [String(nTotal), "total plays"]].map(([v, l]) => (
                <div key={l} className="flex items-baseline gap-2">
                  <span className="tnum font-display text-3xl font-semibold text-zinc-100 light:text-zinc-900">{v}</span>
                  <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">{l}</span>
                </div>
              ))}
            </div>
            <p className="mt-5 max-w-2xl rounded-xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm leading-relaxed text-amber-200/90 light:text-amber-800">
              {data.disclaimer}
            </p>
          </>
        )}
      </div>

      {!data.pending && <ParlayCard parlay={data.parlay ?? null} />}

      {!data.pending && picks.length > 0 && (
        <>
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">Every game</h2>
            <span className="text-sm text-zinc-500">Model vs. Vegas, side by side</span>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {picks.map((p) => <GameCard key={`${p.away}-${p.home}`} p={p} />)}
          </div>
        </>
      )}
    </div>
  );
}
