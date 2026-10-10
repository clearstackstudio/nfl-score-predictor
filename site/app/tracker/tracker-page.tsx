"use client";

import { useEffect, useMemo, useState } from "react";
import { fmtPct } from "../lib/format";

/* ------------------------------------------------------------------ */
/* Types + storage                                                      */
/* ------------------------------------------------------------------ */

type Sport = "nfl" | "cfb" | "nba" | "ncaab" | "mlb" | "other";
type Market = "spread" | "total" | "moneyline" | "prop" | "other";
type Result = "win" | "loss" | "push" | "pending";

type Bet = {
  id: string;
  date: string; // YYYY-MM-DD
  sport: Sport;
  market: Market;
  selection: string;
  odds: number; // American, e.g. -110
  stake: number;
  result: Result;
  confidence?: number; // 1-99, optional "what did you think your chance was?"
};

const LS_KEY = "hl-bet-tracker-v1";

const SPORTS: { id: Sport; label: string }[] = [
  { id: "nfl", label: "NFL" },
  { id: "cfb", label: "NCAAF" },
  { id: "nba", label: "NBA" },
  { id: "ncaab", label: "NCAAB" },
  { id: "mlb", label: "MLB" },
  { id: "other", label: "Other" },
];

const MARKETS: { id: Market; label: string }[] = [
  { id: "spread", label: "Spread" },
  { id: "total", label: "Total" },
  { id: "moneyline", label: "Moneyline" },
  { id: "prop", label: "Prop" },
  { id: "other", label: "Other" },
];

function loadBets(): Bet[] {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) {
      const d = JSON.parse(raw);
      if (Array.isArray(d)) return d as Bet[];
    }
  } catch {
    /* fresh start */
  }
  return [];
}

function saveBets(bets: Bet[]) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(bets));
  } catch {
    /* storage full/blocked — the page still works for this session */
  }
}

/* ------------------------------------------------------------------ */
/* Honest math                                                          */
/* ------------------------------------------------------------------ */

/** American odds -> implied probability (the breakeven rate). */
function impliedProb(odds: number): number {
  if (!Number.isFinite(odds) || odds === 0) return NaN;
  return odds < 0 ? -odds / (-odds + 100) : 100 / (odds + 100);
}

/** Profit in dollars for a graded bet. */
function profitOf(b: Bet): number {
  if (b.result === "win") return b.stake * (b.odds > 0 ? b.odds / 100 : 100 / -b.odds);
  if (b.result === "loss") return -b.stake;
  return 0;
}

function uid(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function todayISO(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fmtMoney(n: number): string {
  const sign = n < 0 ? "-" : n > 0 ? "+" : "";
  return `${sign}$${Math.abs(n).toFixed(n % 1 === 0 ? 0 : 2)}`;
}

/* ------------------------------------------------------------------ */
/* Shared bits                                                          */
/* ------------------------------------------------------------------ */

const cardCls =
  "rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 light:border-zinc-200 light:bg-white";
const labelCls =
  "mb-1 block text-[11px] font-bold uppercase tracking-wider text-zinc-500 light:text-zinc-600";
const inputCls =
  "w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-amber-400 focus:outline-none light:border-zinc-300 light:bg-white light:text-zinc-900 light:placeholder:text-zinc-400";
const thCls =
  "px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-500 light:text-zinc-600";
const tdCls = "px-3 py-2 text-[13px]";
const rowCls = "border-t border-zinc-800 light:border-zinc-200";

function StatCard({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "good" | "bad" | "neutral";
}) {
  const toneCls =
    tone === "good"
      ? "text-emerald-400 light:text-emerald-700"
      : tone === "bad"
        ? "text-amber-400 light:text-amber-700"
        : "text-zinc-100 light:text-zinc-900";
  return (
    <div className={cardCls}>
      <div className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 light:text-zinc-600">
        {label}
      </div>
      <div className={`mt-1 font-display text-3xl font-semibold ${toneCls}`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-zinc-500 light:text-zinc-600">{sub}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Calibration plot — your claimed probability vs your actual hit rate  */
/* ------------------------------------------------------------------ */

const W = 560, H = 430;
const M = { l: 58, r: 20, t: 20, b: 56 };

type CalBin = { label: string; n: number; predicted: number; actual: number };

const BIN_EDGES = [0.5, 0.524, 0.55, 0.6];

function binLabel(lo: number, hi: number | null): string {
  if (lo === 0) return `<${Math.round(hi! * 100)}%`;
  if (hi == null) return `${Math.round(lo * 100)}%+`;
  return `${Math.round(lo * 100)}–${Math.round(hi * 100)}%`;
}

function userBins(bets: Bet[]): CalBin[] {
  const graded = bets.filter(
    (b) => (b.result === "win" || b.result === "loss") && Number.isFinite(impliedProb(b.odds))
  );
  const edges = [0, ...BIN_EDGES, 1];
  const out: CalBin[] = [];
  for (let i = 0; i < edges.length - 1; i++) {
    const lo = edges[i], hi = edges[i + 1];
    let n = 0, wins = 0, sumP = 0;
    for (const b of graded) {
      const p = impliedProb(b.odds);
      if (p >= lo && (i === edges.length - 2 || p < hi)) {
        n++;
        sumP += p;
        if (b.result === "win") wins++;
      }
    }
    if (n > 0) out.push({ label: binLabel(lo, i === edges.length - 2 ? null : hi), n, predicted: sumP / n, actual: wins / n });
  }
  return out;
}

function UserCalibrationPlot({ bins }: { bins: CalBin[] }) {
  const xs: number[] = [], ys: number[] = [];
  for (const b of bins) { xs.push(b.predicted); ys.push(b.actual); }
  if (xs.length === 0) return null;

  let lo = Math.min(0.4, ...xs, ...ys);
  lo = Math.floor(lo * 20) / 20;
  let hi = Math.max(0.65, ...xs, ...ys);
  hi = Math.ceil(hi * 20) / 20;

  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  const X = (v: number) => M.l + ((v - lo) / (hi - lo)) * iw;
  const Y = (v: number) => M.t + (1 - (v - lo) / (hi - lo)) * ih;

  const ticks: number[] = [];
  for (let t = lo; t <= hi + 1e-9; t += 0.05) ticks.push(Math.round(t * 100) / 100);

  const maxN = Math.max(1, ...bins.map((b) => b.n));
  const rOf = (n: number) => 6 + 10 * Math.sqrt(n / maxN);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img"
      aria-label="Your calibration plot: odds-implied probability versus your actual hit rate"
      className="h-auto w-full">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={M.l} x2={W - M.r} y1={Y(t)} y2={Y(t)}
            className="stroke-zinc-800 light:stroke-zinc-200" strokeWidth={t === 0.5 ? 1.5 : 1} />
          <text x={M.l - 8} y={Y(t) + 3.5} textAnchor="end" fontSize={10}
            className="fill-zinc-500 font-mono">{fmtPct(t)}</text>
          <line x1={X(t)} x2={X(t)} y1={M.t} y2={H - M.b}
            className="stroke-zinc-800 light:stroke-zinc-200" strokeWidth={1} />
          <text x={X(t)} y={H - M.b + 18} textAnchor="middle" fontSize={10}
            className="fill-zinc-500 font-mono">{fmtPct(t)}</text>
        </g>
      ))}
      {/* ideal diagonal */}
      <line x1={X(lo)} y1={Y(lo)} x2={X(hi)} y2={Y(hi)}
        className="stroke-zinc-500" strokeWidth={1.5} strokeDasharray="6 5" />
      <text x={X(hi) - 4} y={Y(hi) - 8} textAnchor="end" fontSize={10}
        className="fill-zinc-500 italic">perfect calibration</text>
      {/* your bins */}
      {bins.map((b) => {
        const above = b.actual >= b.predicted;
        return (
          <circle key={b.label} cx={X(b.predicted)} cy={Y(b.actual)} r={rOf(b.n)}
            strokeWidth={2} opacity={0.95}
            className={above
              ? "fill-emerald-400/70 stroke-emerald-300 light:fill-emerald-600/70 light:stroke-emerald-700"
              : "fill-amber-400/70 stroke-amber-300 light:fill-amber-600/70 light:stroke-amber-700"}>
            <title>{`${b.label}: needed ${fmtPct(b.predicted)}, hit ${fmtPct(b.actual)} (n=${b.n})`}</title>
          </circle>
        );
      })}
      <text x={(M.l + W - M.r) / 2} y={H - 8} textAnchor="middle" fontSize={11}
        className="fill-zinc-400 font-semibold light:fill-zinc-600">Breakeven rate (from your odds)</text>
      <text x={16} y={(M.t + H - M.b) / 2} textAnchor="middle" fontSize={11}
        transform={`rotate(-90 16 ${(M.t + H - M.b) / 2})`}
        className="fill-zinc-400 font-semibold light:fill-zinc-600">Your actual hit rate</text>
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Bet form                                                            */
/* ------------------------------------------------------------------ */

const emptyForm = () => ({
  date: todayISO(),
  sport: "nfl" as Sport,
  market: "spread" as Market,
  selection: "",
  odds: "-110",
  stake: "100",
  result: "pending" as Result,
  confidence: "",
});

function BetForm({ onAdd }: { onAdd: (b: Bet) => void }) {
  const [f, setF] = useState(emptyForm());
  const [err, setErr] = useState<string | null>(null);

  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));

  const submit = () => {
    const odds = Number(f.odds);
    const stake = Number(f.stake);
    const conf = f.confidence.trim() === "" ? undefined : Number(f.confidence);
    if (!f.selection.trim()) return setErr("Give the bet a name — e.g. “Chiefs -3”.");
    if (!Number.isFinite(odds) || odds === 0 || Math.abs(odds) < 100)
      return setErr("Odds look off — use American format like -110 or +150.");
    if (!Number.isFinite(stake) || stake <= 0) return setErr("Stake must be more than 0.");
    if (conf !== undefined && (!Number.isFinite(conf) || conf <= 0 || conf >= 100))
      return setErr("Confidence must be between 1 and 99.");
    setErr(null);
    onAdd({
      id: uid(),
      date: f.date,
      sport: f.sport,
      market: f.market,
      selection: f.selection.trim(),
      odds,
      stake,
      result: f.result,
      confidence: conf,
    });
    setF(emptyForm());
  };

  return (
    <div className={cardCls}>
      <div className="font-display text-xl font-semibold uppercase tracking-wide">Log a bet</div>
      <p className="mt-1 text-sm text-zinc-500 light:text-zinc-600">
        Every bet you log becomes part of your receipt. Nothing leaves your browser.
      </p>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div>
          <label className={labelCls} htmlFor="bt-date">Date</label>
          <input id="bt-date" type="date" value={f.date} onChange={(e) => set("date", e.target.value)} className={inputCls} />
        </div>
        <div>
          <label className={labelCls} htmlFor="bt-sport">Sport</label>
          <select id="bt-sport" value={f.sport} onChange={(e) => set("sport", e.target.value)} className={inputCls}>
            {SPORTS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
        </div>
        <div>
          <label className={labelCls} htmlFor="bt-market">Market</label>
          <select id="bt-market" value={f.market} onChange={(e) => set("market", e.target.value)} className={inputCls}>
            {MARKETS.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
          </select>
        </div>
        <div>
          <label className={labelCls} htmlFor="bt-result">Result</label>
          <select id="bt-result" value={f.result} onChange={(e) => set("result", e.target.value)} className={inputCls}>
            <option value="pending">Pending</option>
            <option value="win">Win</option>
            <option value="loss">Loss</option>
            <option value="push">Push</option>
          </select>
        </div>
        <div className="col-span-2">
          <label className={labelCls} htmlFor="bt-selection">Your pick</label>
          <input id="bt-selection" value={f.selection} onChange={(e) => set("selection", e.target.value)}
            placeholder="Chiefs -3" className={inputCls} />
        </div>
        <div>
          <label className={labelCls} htmlFor="bt-odds">Odds (American)</label>
          <input id="bt-odds" value={f.odds} onChange={(e) => set("odds", e.target.value)}
            placeholder="-110" inputMode="numeric" className={`${inputCls} font-mono`} />
        </div>
        <div>
          <label className={labelCls} htmlFor="bt-stake">Stake ($)</label>
          <input id="bt-stake" value={f.stake} onChange={(e) => set("stake", e.target.value)}
            placeholder="100" inputMode="decimal" className={`${inputCls} font-mono`} />
        </div>
        <div className="col-span-2 sm:col-span-4">
          <label className={labelCls} htmlFor="bt-conf">
            Your estimated win chance % <span className="font-normal normal-case text-zinc-600">(optional — powers the overconfidence check)</span>
          </label>
          <input id="bt-conf" value={f.confidence} onChange={(e) => set("confidence", e.target.value)}
            placeholder="e.g. 60" inputMode="numeric" className={`${inputCls} font-mono max-w-[160px]`} />
        </div>
      </div>
      {err && <div className="mt-3 text-sm font-semibold text-amber-400 light:text-amber-700">{err}</div>}
      <button
        onClick={submit}
        className="mt-4 rounded-lg bg-amber-400 px-5 py-2.5 text-sm font-bold uppercase tracking-wider text-zinc-950 transition hover:bg-amber-300"
      >
        Add to my receipt
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Bet list                                                            */
/* ------------------------------------------------------------------ */

function resultBadge(r: Result) {
  const cls =
    r === "win"
      ? "bg-emerald-400/15 text-emerald-300 light:text-emerald-700"
      : r === "loss"
        ? "bg-amber-400/15 text-amber-300 light:text-amber-700"
        : "bg-zinc-700/40 text-zinc-400 light:bg-zinc-200 light:text-zinc-600";
  return (
    <span className={`rounded px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ${cls}`}>
      {r}
    </span>
  );
}

function BetList({ bets, onDelete, onSetResult }: {
  bets: Bet[];
  onDelete: (id: string) => void;
  onSetResult: (id: string, r: Result) => void;
}) {
  const sorted = [...bets].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  if (sorted.length === 0) return null;
  const sportLabel = (id: Sport) => SPORTS.find((s) => s.id === id)?.label ?? id;
  return (
    <div className={cardCls}>
      <div className="font-display text-xl font-semibold uppercase tracking-wide">
        Your bets <span className="text-zinc-500">({bets.length})</span>
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left">
              <th className={thCls}>Date</th>
              <th className={thCls}>Pick</th>
              <th className={thCls}>Odds</th>
              <th className={thCls}>Stake</th>
              <th className={thCls}>Result</th>
              <th className={thCls}>P/L</th>
              <th className={thCls}><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((b) => {
              const pl = profitOf(b);
              return (
                <tr key={b.id} className={rowCls}>
                  <td className={`${tdCls} whitespace-nowrap font-mono text-zinc-400 light:text-zinc-600`}>{b.date}</td>
                  <td className={tdCls}>
                    <span className="font-semibold">{b.selection}</span>
                    <span className="ml-2 text-xs text-zinc-500">{sportLabel(b.sport)} · {b.market}</span>
                  </td>
                  <td className={`${tdCls} font-mono`}>{b.odds > 0 ? `+${b.odds}` : b.odds}</td>
                  <td className={`${tdCls} font-mono`}>${b.stake}</td>
                  <td className={tdCls}>
                    {b.result === "pending" ? (
                      <span className="inline-flex gap-1">
                        {(["win", "loss", "push"] as Result[]).map((r) => (
                          <button key={r} onClick={() => onSetResult(b.id, r)}
                            className="rounded border border-zinc-700 px-1.5 py-0.5 text-[11px] font-bold uppercase text-zinc-400 hover:border-amber-400 hover:text-amber-300 light:border-zinc-300 light:text-zinc-600">
                            {r === "win" ? "W" : r === "loss" ? "L" : "P"}
                          </button>
                        ))}
                      </span>
                    ) : (
                      resultBadge(b.result)
                    )}
                  </td>
                  <td className={`${tdCls} font-mono font-semibold ${pl > 0 ? "text-emerald-400 light:text-emerald-700" : pl < 0 ? "text-amber-400 light:text-amber-700" : "text-zinc-500"}`}>
                    {b.result === "pending" ? "—" : fmtMoney(pl)}
                  </td>
                  <td className={tdCls}>
                    <button onClick={() => onDelete(b.id)} aria-label={`Delete ${b.selection}`}
                      className="text-zinc-600 hover:text-red-400 light:text-zinc-400">×</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-zinc-600 light:text-zinc-500">
        Tap W / L / P on a pending bet to grade it. Everything stays in this browser — we never see your bets.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Analytics                                                           */
/* ------------------------------------------------------------------ */

type Stats = {
  graded: Bet[];
  w: number; l: number; p: number;
  winRate: number | null;
  staked: number;
  profit: number;
  roi: number | null;
  breakeven: number | null;
};

function computeStats(bets: Bet[]): Stats {
  const graded = bets.filter((b) => b.result === "win" || b.result === "loss" || b.result === "push");
  let w = 0, l = 0, p = 0, staked = 0, profit = 0, sumImp = 0, nImp = 0;
  for (const b of graded) {
    if (b.result === "win") w++;
    else if (b.result === "loss") l++;
    else p++;
    if (b.result !== "push") {
      staked += b.stake;
      const ip = impliedProb(b.odds);
      if (Number.isFinite(ip)) { sumImp += ip * b.stake; nImp += b.stake; }
    }
    profit += profitOf(b);
  }
  const decided = w + l;
  return {
    graded,
    w, l, p,
    winRate: decided ? w / decided : null,
    staked,
    profit,
    roi: staked ? profit / staked : null,
    breakeven: nImp ? sumImp / nImp : null,
  };
}

function BreakdownTable({ title, rows }: {
  title: string;
  rows: { label: string; w: number; l: number; profit: number; staked: number }[];
}) {
  const shown = rows.filter((r) => r.w + r.l > 0);
  if (shown.length === 0) return null;
  return (
    <div>
      <div className="mb-2 text-xs font-bold uppercase tracking-wider text-zinc-400 light:text-zinc-600">{title}</div>
      <div className="overflow-x-auto rounded-xl border border-zinc-800 light:border-zinc-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-zinc-900/60 text-left light:bg-zinc-100">
              <th className={thCls}>Split</th>
              <th className={thCls}>Record</th>
              <th className={thCls}>Win%</th>
              <th className={thCls}>Profit</th>
              <th className={thCls}>ROI</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => {
              const wr = r.w / (r.w + r.l);
              const roi = r.staked ? r.profit / r.staked : null;
              return (
                <tr key={r.label} className={rowCls}>
                  <td className="px-3 py-2 font-semibold">{r.label}</td>
                  <td className={`${tdCls} font-mono`}>{r.w}-{r.l}</td>
                  <td className={`${tdCls} font-mono font-semibold ${wr >= 0.524 ? "text-emerald-400 light:text-emerald-700" : "text-zinc-300 light:text-zinc-700"}`}>
                    {fmtPct(wr)}
                  </td>
                  <td className={`${tdCls} font-mono font-semibold ${r.profit > 0 ? "text-emerald-400 light:text-emerald-700" : r.profit < 0 ? "text-amber-400 light:text-amber-700" : "text-zinc-500"}`}>
                    {fmtMoney(r.profit)}
                  </td>
                  <td className={`${tdCls} font-mono`}>{roi == null ? "—" : `${roi >= 0 ? "+" : ""}${(roi * 100).toFixed(1)}%`}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function breakdown(bets: Bet[], key: (b: Bet) => string, labelOf: (k: string) => string) {
  const m = new Map<string, { w: number; l: number; profit: number; staked: number }>();
  for (const b of bets) {
    if (b.result !== "win" && b.result !== "loss") continue;
    const k = key(b);
    const e = m.get(k) ?? { w: 0, l: 0, profit: 0, staked: 0 };
    if (b.result === "win") e.w++; else e.l++;
    e.staked += b.stake;
    e.profit += profitOf(b);
    m.set(k, e);
  }
  return [...m.entries()].map(([k, v]) => ({ label: labelOf(k), ...v }));
}

/* ------------------------------------------------------------------ */
/* Honest insights — computed from your data, plain language           */
/* ------------------------------------------------------------------ */

function Insights({ bets, stats }: { bets: Bet[]; stats: Stats }) {
  const notes: { tone: "good" | "bad" | "neutral"; text: React.ReactNode }[] = [];

  if (stats.breakeven != null && stats.winRate != null && stats.w + stats.l >= 10) {
    const gap = stats.winRate - stats.breakeven;
    notes.push({
      tone: gap >= 0 ? "good" : "bad",
      text: (
        <>
          At your average odds you needed <strong>{fmtPct(stats.breakeven)}</strong> to break
          even — you hit <strong>{fmtPct(stats.winRate)}</strong>.{" "}
          {gap >= 0 ? "You're beating the price. Keep doing exactly this." : "The vig is eating you. Either find better prices or stop."}
        </>
      ),
    });
  }

  // Overconfidence check: user's own estimates vs reality
  const conf = bets.filter(
    (b) => (b.result === "win" || b.result === "loss") && b.confidence != null
  );
  if (conf.length >= 10) {
    const hi = conf.filter((b) => b.confidence! >= 60);
    if (hi.length >= 5) {
      const actual = hi.filter((b) => b.result === "win").length / hi.length;
      const claimed = hi.reduce((a, b) => a + b.confidence! / 100, 0) / hi.length;
      notes.push({
        tone: actual >= claimed ? "good" : "bad",
        text: (
          <>
            Your high-confidence bets (you said ≥60%, n={hi.length}) hit{" "}
            <strong>{fmtPct(actual)}</strong> vs the <strong>{fmtPct(claimed)}</strong> you
            expected.{" "}
            {actual >= claimed - 0.03
              ? "Your read on your own edge is honest."
              : "You're overconfident — your “locks” aren't. Size them like coin flips until the receipt says otherwise."}
          </>
        ),
      });
    }
  }

  // Best / worst market
  const byMarket = breakdown(bets, (b) => b.market, (k) => MARKETS.find((m) => m.id === k)?.label ?? k)
    .filter((r) => r.w + r.l >= 5)
    .sort((a, b) => b.profit - a.profit);
  if (byMarket.length >= 2) {
    const best = byMarket[0], worst = byMarket[byMarket.length - 1];
    if (best.profit > 0 || worst.profit < 0) {
      notes.push({
        tone: "neutral",
        text: (
          <>
            Your best market is <strong>{best.label}</strong> ({fmtMoney(best.profit)}) and your
            worst is <strong>{worst.label}</strong> ({fmtMoney(worst.profit)}). The honest
            question: would you be up more if you only bet the first?
          </>
        ),
      });
    }
  }

  // Sample-size honesty
  if (stats.w + stats.l > 0 && stats.w + stats.l < 30) {
    notes.push({
      tone: "neutral",
      text: (
        <>
          Small sample (n={stats.w + stats.l}) — nothing here is conclusive yet. The receipt
          gets honest around 100+ graded bets. Keep logging.
        </>
      ),
    });
  }

  if (notes.length === 0) return null;
  return (
    <div className={cardCls}>
      <div className="font-display text-xl font-semibold uppercase tracking-wide">What your receipt says</div>
      <ul className="mt-3 space-y-3">
        {notes.map((n, i) => (
          <li key={i} className="flex gap-3 text-sm leading-relaxed">
            <span
              aria-hidden="true"
              className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                n.tone === "good" ? "bg-emerald-400" : n.tone === "bad" ? "bg-amber-400" : "bg-zinc-500"
              }`}
            />
            <span className="text-zinc-300 light:text-zinc-700">{n.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-zinc-700 bg-zinc-900/30 p-10 text-center light:border-zinc-300 light:bg-zinc-50">
      <div className="font-display text-3xl font-semibold uppercase tracking-wide">
        Your receipt starts here
      </div>
      <p className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        Most bettors remember their wins and forget their losses. This page does the
        opposite: log every bet, and it&rsquo;ll show you your real record, your real
        ROI, and whether you&rsquo;re as good as you think — plotted the same way we
        grade our own models. No account, nothing leaves your browser.
      </p>
      <p className="mt-4 text-sm font-semibold text-amber-300 light:text-amber-700">
        Log your first bet above to start building your receipt.
      </p>
    </div>
  );
}

export default function TrackerPage() {
  const [bets, setBets] = useState<Bet[]>([]);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setBets(loadBets());
    setMounted(true);
  }, []);

  const add = (b: Bet) => {
    setBets((prev) => {
      const next = [b, ...prev];
      saveBets(next);
      return next;
    });
  };
  const remove = (id: string) => {
    setBets((prev) => {
      const next = prev.filter((b) => b.id !== id);
      saveBets(next);
      return next;
    });
  };
  const setResult = (id: string, r: Result) => {
    setBets((prev) => {
      const next = prev.map((b) => (b.id === id ? { ...b, result: r } : b));
      saveBets(next);
      return next;
    });
  };
  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(bets, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "honest-line-bet-tracker.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const stats = useMemo(() => computeStats(bets), [bets]);
  const bins = useMemo(() => userBins(bets), [bets]);
  const bySport = useMemo(
    () => breakdown(bets, (b) => b.sport, (k) => SPORTS.find((s) => s.id === k)?.label ?? k),
    [bets]
  );
  const byMarket = useMemo(
    () => breakdown(bets, (b) => b.market, (k) => MARKETS.find((m) => m.id === k)?.label ?? k),
    [bets]
  );
  const byMonth = useMemo(
    () => breakdown(bets, (b) => b.date.slice(0, 7), (k) => k),
    [bets]
  );

  if (!mounted) return null;
  const hasBets = bets.length > 0;
  const hasGraded = stats.w + stats.l > 0;

  return (
    <div>
      {/* Hero */}
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-400/90 light:text-emerald-700">
        <span className="h-px w-8 bg-emerald-400/60 light:bg-emerald-600/70" aria-hidden="true" />
        Your bets · your receipt
      </div>
      <h1 className="mt-3 max-w-3xl font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide sm:text-6xl">
        Are you as good as you <span className="text-emerald-400 light:text-emerald-600">think</span>?
      </h1>
      <p className="mt-4 max-w-3xl text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
        Log your own bets and get the Honest Line treatment: real record, real ROI with
        the vig math shown, and a calibration plot of your odds against your actual hit
        rate. We grade our models in public — this is the same mirror, for you.
      </p>

      <div className="mt-8 space-y-6">
        <BetForm onAdd={add} />

        {!hasBets ? (
          <EmptyState />
        ) : (
          <>
            {/* Headline stats */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <StatCard
                label="Record"
                value={`${stats.w}-${stats.l}${stats.p ? `-${stats.p}` : ""}`}
                sub={hasGraded ? `${stats.w + stats.l + stats.p} graded bets` : "No graded bets yet"}
              />
              <StatCard
                label="Win rate"
                value={fmtPct(stats.winRate)}
                sub={stats.breakeven != null ? `Needed ${fmtPct(stats.breakeven)} to break even` : undefined}
                tone={stats.winRate != null && stats.breakeven != null ? (stats.winRate >= stats.breakeven ? "good" : "bad") : "neutral"}
              />
              <StatCard
                label="Profit / loss"
                value={fmtMoney(stats.profit)}
                sub={stats.staked ? `On ${fmtMoney(stats.staked)} staked` : undefined}
                tone={stats.profit > 0 ? "good" : stats.profit < 0 ? "bad" : "neutral"}
              />
              <StatCard
                label="ROI"
                value={stats.roi == null ? "—" : `${stats.roi >= 0 ? "+" : ""}${(stats.roi * 100).toFixed(1)}%`}
                sub="After the vig — the only number that matters"
                tone={stats.roi == null ? "neutral" : stats.roi > 0 ? "good" : "bad"}
              />
            </div>

            <Insights bets={bets} stats={stats} />

            {/* Calibration */}
            <div className={cardCls}>
              <div className="font-display text-xl font-semibold uppercase tracking-wide">
                Your calibration
              </div>
              <p className="mt-1 max-w-2xl text-sm text-zinc-500 light:text-zinc-600">
                Each dot is a group of your bets at similar odds. Bottom axis: the breakeven
                rate your odds demanded. Side axis: how often you actually won. Dots above
                the dashed line beat the price; below it, the vig won.{" "}
                {bins.length > 0 && bins.every((b) => b.n < 10) && (
                  <span className="font-semibold text-amber-300 light:text-amber-700">
                    Small samples — these dots will move a lot as you log more.
                  </span>
                )}
              </p>
              {bins.length > 0 ? (
                <div className="mt-4">
                  <UserCalibrationPlot bins={bins} />
                </div>
              ) : (
                <p className="mt-4 text-sm text-zinc-500 light:text-zinc-600">
                  Grade a few bets (tap W / L below) and your plot appears here.
                </p>
              )}
            </div>

            {/* Breakdowns */}
            <div className="grid gap-6 lg:grid-cols-3">
              <BreakdownTable title="By sport" rows={bySport} />
              <BreakdownTable title="By market" rows={byMarket} />
              <BreakdownTable title="By month" rows={byMonth} />
            </div>

            <BetList bets={bets} onDelete={remove} onSetResult={setResult} />

            <div className="flex items-center justify-between">
              <p className="text-xs text-zinc-600 light:text-zinc-500">
                Stored only in this browser ({LS_KEY}). Clearing site data deletes your bets.
              </p>
              <button onClick={exportJSON}
                className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-bold uppercase tracking-wider text-zinc-300 hover:border-amber-400 hover:text-amber-300 light:border-zinc-300 light:text-zinc-700">
                Export JSON
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
