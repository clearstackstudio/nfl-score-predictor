"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  fetchScoreboard,
  fetchGameDetail,
  type LiveGame,
  type GameDetail,
  type League,
} from "../lib/espn";

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-60" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-400 light:bg-amber-600" />
      </span>
      {children}
    </div>
  );
}

function TeamMark({ logo, abbr, size = 28 }: { logo: string; abbr: string; size?: number }) {
  if (!logo) {
    return (
      <span
        className="inline-flex shrink-0 items-center justify-center rounded-full bg-zinc-800 font-mono font-bold text-zinc-400 light:bg-zinc-200 light:text-zinc-600"
        style={{ width: size, height: size, fontSize: size * 0.35 }}
      >
        {abbr.slice(0, 2)}
      </span>
    );
  }
  return (
    <img src={logo} alt={`${abbr} logo`} width={size} height={size} className="shrink-0" loading="lazy" />
  );
}

function WinProbChart({ points, homeAbbr, awayAbbr }: { points: { homeWinPct: number }[]; homeAbbr: string; awayAbbr: string }) {
  const [open, setOpen] = useState(true);
  const { path, area } = useMemo(() => {
    if (points.length < 2) return { path: "", area: "" };
    const W = 600, H = 120, PAD = 8;
    const x = (i: number) => PAD + (i / (points.length - 1)) * (W - 2 * PAD);
    const y = (p: number) => PAD + (1 - p) * (H - 2 * PAD);
    const pts = points.map((pt, i) => `${x(i).toFixed(1)},${y(pt.homeWinPct).toFixed(1)}`);
    return {
      path: `M${pts.join(" L")}`,
      area: `M${x(0).toFixed(1)},${H - PAD} L${pts.join(" L")} L${x(points.length - 1).toFixed(1)},${H - PAD} Z`,
    };
  }, [points]);
  if (points.length < 2) return null;
  const last = points[points.length - 1].homeWinPct;
  return (
    <div className="rounded-2xl border border-white/15 bg-zinc-900/70 p-5 light:border-zinc-200 light:bg-white">
      <div className="flex items-baseline justify-between">
        <button onClick={() => setOpen(!open)} aria-expanded={open} className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-zinc-300 light:text-zinc-600">
          Win probability
          <CollapsePill open={open} />
        </button>
        <div className="tnum font-mono text-base font-bold">
          <span className="text-zinc-300 light:text-zinc-600">{awayAbbr} {Math.round((1 - last) * 100)}%</span>
          <span className="mx-2 text-zinc-600 light:text-zinc-300">·</span>
          <span className="text-amber-300 light:text-amber-600">{homeAbbr} {Math.round(last * 100)}%</span>
        </div>
      </div>
      <CollapseRegion open={open}>
        <svg viewBox="0 0 600 120" className="mt-3 h-32 w-full" preserveAspectRatio="none" role="img" aria-label="Win probability chart">
          <line x1="0" y1="60" x2="600" y2="60" stroke="#52525b" strokeDasharray="4 4" strokeWidth="1" />
          <path d={area} fill="rgba(251,191,36,0.15)" className="fade-in" />
          <path d={path} fill="none" stroke="#fbbf24" strokeWidth="2.5" vectorEffect="non-scaling-stroke" pathLength={1} className="chart-draw" />
        </svg>
        <div className="mt-2 flex justify-between text-[11px] font-medium text-zinc-400 light:text-zinc-500">
          <span>Kickoff</span>
          <span>Now</span>
        </div>
      </CollapseRegion>
    </div>
  );
}

/** Gamecast, modeled on ESPN's current design: a "Current drive" header, a
 * Down / Ball-on readout, then a flat gray field \u2014 alternating 10-yard
 * mowing stripes, white yard lines, a dashed hash row, team-colored end
 * zones with the nickname vertical and a small goalpost, the ball as the
 * possessing team's logo pin with a dashed line-of-scrimmage drop, and a
 * yellow first-down line. Yard numbers sit in a row below the field, as
 * ESPN draws them, and a last-play panel closes the strip. The plane is
 * tilted in perspective at the owner's request — a 3D stadium feel on
 * ESPN's flat design, shortened to 88% width, the logo pin counter-rotated
 * to stand upright off the surface. The field is a
 * self-contained graphic with fixed colors in both schemes. Ball position
 * is the feed's absolute 0\u2013100 yard line; which end is being attacked
 * follows from the spot's yards-to-endzone. */
function GamecastStrip({ detail }: { detail: GameDetail }) {
  const drive = detail.drives[0];
  const spotPlay = drive?.plays.find((p) => p.spot);
  // ESPN-style update pulse: when a new play lands, the pin rings once.
  const [pulse, setPulse] = useState(false);
  const prevPlayId = useRef<string | null>(null);
  useEffect(() => {
    const id = spotPlay?.id ?? null;
    if (id && prevPlayId.current && prevPlayId.current !== id) {
      setPulse(true);
      const t = setTimeout(() => setPulse(false), 1300);
      prevPlayId.current = id;
      return () => clearTimeout(t);
    }
    prevPlayId.current = id;
  }, [spotPlay?.id]);
  if (detail.game.state !== "in" || !drive || !spotPlay?.spot) return null;
  const spot = spotPlay.spot;
  const g = detail.game;
  const offense = drive.teamAbbr;
  const defense = offense === g.awayAbbr ? g.homeAbbr : g.awayAbbr;
  // Orientation comes from the Ball-on text ESPN itself prints ("SF 13"),
  // never from the raw yard-line fields: their absolute frame flips
  // between halves, which put the pin on the wrong side in 8 of 62 spots
  // replayed from the 2026-10-19 WAS@SF game. The field always faces the
  // possessing team — their end zone left, the target end zone right —
  // and the pin sits exactly the stated yards from the stated end zone.
  const terr =
    /^([A-Z]{2,4}) (\d{1,2})$/.exec(spot.text) ??
    /at ([A-Z]{2,4}) (\d{1,2})\b/.exec(spot.downDistanceText);
  let ballX: number;
  if (terr) {
    ballX = terr[1] === offense ? parseInt(terr[2], 10) : 100 - parseInt(terr[2], 10);
  } else if (spot.text === "50" || spot.downDistanceText.endsWith("at 50")) {
    ballX = 50; // midfield: the feed names no territory team
  } else {
    return null;
  }
  const leftAbbr = offense;
  const rightAbbr = defense;
  const meta = (abbr: string) =>
    abbr === g.awayAbbr
      ? { color: g.awayColor, alt: g.awayAltColor, name: g.awayName, logo: g.awayLogo }
      : { color: g.homeColor, alt: g.homeAltColor, name: g.homeName, logo: g.homeLogo };
  const offMeta = meta(offense);
  const nickname = (name: string) => (name.split(" ").pop() ?? "").toUpperCase();
  const distMatch = /& (\d+)\b/.exec(spot.downDistanceText);
  const dist = distMatch ? parseInt(distMatch[1], 10) : spot.distance;
  const firstDown =
    dist > 0 && !spot.downDistanceText.includes("Goal") ? ballX + dist : null;
  const lastPlay = drive.plays.find((p) => p.text) ?? spotPlay;
  const downText = spot.downDistanceText.includes(" at ")
    ? spot.downDistanceText.split(" at ")[0]
    : spot.downDistanceText;

  const EndZone = ({ abbr, side }: { abbr: string; side: "left" | "right" }) => {
    const m = meta(abbr);
    return (
      <div
        className="relative flex w-[9%] items-center justify-center"
        style={{ backgroundColor: m.color ? `#${m.color}` : "#3f3f46" }}
      >
        <span
          className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-white"
          style={{ writingMode: "vertical-rl", transform: side === "left" ? "rotate(180deg)" : undefined }}
        >
          {nickname(m.name)}
        </span>
        <svg
          className={`absolute top-1/2 h-5 w-2.5 -translate-y-1/2 text-yellow-400 ${side === "left" ? "-left-px" : "-right-px"}`}
          viewBox="0 0 10 20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          aria-hidden="true"
        >
          <path d="M1.5 1v6M8.5 1v6M1.5 7h7M5 7v12" />
        </svg>
      </div>
    );
  };

  return (
    <div className="mt-4 border-t border-white/10 pt-4 light:border-zinc-100">
      <div key={drive.id} className="fade-slide-in flex flex-wrap items-center gap-x-2 gap-y-1">
        <TeamMark logo={drive.teamLogo} abbr={offense} size={20} />
        {drive.isCurrent && <BallIcon size={18} />}
        <span className="text-xs font-bold uppercase tracking-[0.14em] text-zinc-200 light:text-zinc-700">
          {drive.isCurrent ? "Current drive" : "Last drive"}
        </span>
        {drive.description && (
          <span className="text-xs text-zinc-400 light:text-zinc-500">{drive.description}</span>
        )}
      </div>

      <div className="mt-2.5 flex gap-10">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Down</div>
          <div className="mt-0.5 text-sm font-bold text-zinc-100 light:text-zinc-900">{downText || "\u2014"}</div>
        </div>
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Ball on</div>
          <div className="mt-0.5 text-sm font-bold text-zinc-100 light:text-zinc-900">{spot.text || "\u2014"}</div>
        </div>
      </div>

      <div className="gamecast-in mx-auto mt-1 w-[88%]" style={{ perspective: "520px" }}>
        <div
          className="relative flex h-28 overflow-hidden rounded-lg shadow-[0_16px_20px_-10px_rgba(0,0,0,0.5)]"
          role="img"
          aria-label={`Gamecast field: ${spot.downDistanceText || `${offense} ball`}`}
          style={{ transform: "rotateX(34deg)", transformOrigin: "50% 100%" }}
        >
        <EndZone abbr={leftAbbr} side="left" />
        <div
          className="relative flex-1"
          style={{
            background:
              "repeating-linear-gradient(90deg, #e8e8eb 0%, #e8e8eb 10%, #dadade 10%, #dadade 20%)",
          }}
        >
          {[10, 20, 30, 40, 50, 60, 70, 80, 90].map((y) => (
            <span key={y} className="absolute inset-y-0 w-px bg-white/80" style={{ left: `${y}%` }} />
          ))}
          <span className="absolute inset-x-0 top-1/2 border-t border-dashed border-zinc-500/50" />
          {firstDown !== null && firstDown > 0 && firstDown < 100 && (
            <span className="absolute inset-y-0 w-[2.5px] bg-yellow-400 transition-[left] duration-1000 ease-[cubic-bezier(0.22,0.8,0.32,1)]" style={{ left: `${firstDown}%` }} />
          )}
          <div className="absolute z-10 transition-[left] duration-1000 ease-[cubic-bezier(0.22,0.8,0.32,1)]" style={{ left: `${ballX}%`, top: "50%" }}>
            <div className="absolute left-1/2 top-0 h-6 w-px -translate-x-1/2 border-l border-dashed border-zinc-800/60" />
            <div
              className="flex flex-col items-center"
              style={{ transform: "translate(-50%, -112%) rotateX(-34deg)", transformOrigin: "50% 100%" }}
            >
              <div
                className={`flex h-7 w-7 items-center justify-center rounded-full bg-white shadow-md ring-2 ring-amber-400${pulse ? " pin-pulse" : ""}`}
                style={offMeta.alt ? { ["--tw-ring-color" as string]: `#${offMeta.alt}` } : undefined}
              >
                <TeamMark logo={offMeta.logo} abbr={offense} size={19} />
              </div>
              <div className="h-0 w-0 border-x-[5px] border-t-[7px] border-x-transparent border-t-white" />
            </div>
          </div>
        </div>
          <EndZone abbr={rightAbbr} side="right" />
          <span className="pointer-events-none absolute inset-0 z-[5] bg-gradient-to-b from-black/25 via-transparent to-black/20" />
        </div>
        <div className="h-[7px] rounded-b-lg bg-gradient-to-b from-zinc-400 to-zinc-600" />
      </div>

      <div className="mx-auto mt-1 flex h-4 w-[88%] text-[10px] font-medium text-zinc-400 light:text-zinc-500">
        <div className="w-[9%] text-center font-bold">{leftAbbr}</div>
        <div className="relative flex-1">
          {[10, 20, 30, 40, 50, 60, 70, 80, 90].map((y) => (
            <span key={y} className="absolute -translate-x-1/2" style={{ left: `${y}%` }}>
              {y <= 50 ? y : 100 - y}
            </span>
          ))}
        </div>
        <div className="w-[9%] text-center font-bold">{rightAbbr}</div>
      </div>

      {lastPlay.text && (
        <div key={lastPlay.id} className="play-flash mt-2 rounded-xl bg-zinc-950/50 px-4 py-3 light:bg-zinc-50">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-bold text-zinc-100 light:text-zinc-900">
              {lastPlay.typeText ?? "Play"}
            </span>
            <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-300 light:bg-zinc-200 light:text-zinc-600">
              Last play
            </span>
          </div>
          <p className="mt-1 text-sm leading-relaxed text-zinc-400 light:text-zinc-600">{lastPlay.text}</p>
        </div>
      )}
    </div>
  );
}

function BallIcon({ size = 13 }: { size?: number }) {
  return (
    <svg aria-label="Possession" role="img" width={size} height={size} viewBox="0 0 16 16" className="shrink-0 text-amber-400 light:text-amber-600">
      <ellipse cx="8" cy="8" rx="7" ry="4.6" transform="rotate(-30 8 8)" fill="currentColor" />
      <line x1="6.2" y1="6.4" x2="9.8" y2="9.6" stroke="#09090b" strokeWidth="1.1" strokeLinecap="round" transform="rotate(-30 8 8)" />
      <line x1="8" y1="4.6" x2="8" y2="6.2" stroke="#09090b" strokeWidth="1" strokeLinecap="round" transform="rotate(-30 8 8)" />
      <line x1="8" y1="9.8" x2="8" y2="11.4" stroke="#09090b" strokeWidth="1" strokeLinecap="round" transform="rotate(-30 8 8)" />
    </svg>
  );
}

/** Chevron for a collapsible card header; points right when folded. */
function Chevron({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 20 20" className={`h-4 w-4 shrink-0 text-zinc-400 transition-transform duration-300 light:text-zinc-500 ${open ? "" : "-rotate-90"}`} fill="none" aria-hidden="true">
      <path d="M5 7.5 10 12.5 15 7.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Labeled Collapse/Expand pill shown in each card's toggle control. */
function CollapsePill({ open }: { open: boolean }) {
  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-white/15 bg-white/5 px-2.5 py-1 text-[11px] font-semibold normal-case tracking-normal text-zinc-300 light:border-zinc-300 light:bg-zinc-50 light:text-zinc-600">
      {open ? "Collapse" : "Expand"}
      <Chevron open={open} />
    </span>
  );
}

/** Smoothly folds its children away (grid-rows animation) when closed. */
function CollapseRegion({ open, children }: { open: boolean; children: ReactNode }) {
  return (
    <div className={`grid transition-all duration-300 ease-out ${open ? "[grid-template-rows:1fr] opacity-100" : "[grid-template-rows:0fr] opacity-0"}`}>
      <div className="min-h-0 overflow-hidden">{children}</div>
    </div>
  );
}

/** Column header for period i (0-based): Q1..Q4, then OT, 2OT… (basketball: P1, P2…). */
function periodLabel(i: number, football: boolean): string {
  if (!football) return `P${i + 1}`;
  return i < 4 ? `Q${i + 1}` : i === 4 ? "OT" : `${i - 3}OT`;
}

/** One game in the ESPN-style scoreboard list: status rail + team rows + linescore. */
function ScoreboardRow({ g, selected, onSelect, football }: { g: LiveGame; selected: boolean; onSelect: () => void; football: boolean }) {
  const teams = [
    { abbr: g.awayAbbr, score: g.awayScore, logo: g.awayLogo, record: g.awayRecord, lines: g.awayLinescores },
    { abbr: g.homeAbbr, score: g.homeScore, logo: g.homeLogo, record: g.homeRecord, lines: g.homeLinescores },
  ];
  const periods = Math.max(g.awayLinescores.length, g.homeLinescores.length);
  return (
    <button
      onClick={onSelect}
      aria-pressed={selected}
      className={`block w-full text-left transition ${
        selected
          ? "bg-amber-400/[0.08] light:bg-amber-400/15"
          : "hover:bg-white/[0.04] light:hover:bg-zinc-50"
      }`}
    >
      <div className="flex">
        <div className="flex w-[92px] shrink-0 flex-col justify-center border-r border-white/10 px-3 py-2.5 light:border-zinc-200">
          <span className={`text-[11px] font-bold uppercase tracking-wider ${g.state === "in" ? "text-amber-400 light:text-amber-600" : "text-zinc-400 light:text-zinc-500"}`}>
            {g.state === "in" ? "● Live" : g.state === "post" ? "Final" : "Upcoming"}
          </span>
          {g.detail && (
            <span className="tnum mt-0.5 text-[11px] leading-tight text-zinc-400 light:text-zinc-500">{g.detail}</span>
          )}
        </div>
        <div className="min-w-0 flex-1 py-1">
          {periods > 0 && (
            <div className="hidden items-center px-3 pt-1 sm:flex" aria-hidden="true">
              <span className="flex-1" />
              {Array.from({ length: periods }, (_, i) => (
                <span key={i} className="w-7 text-right text-[10px] font-semibold uppercase tracking-wider text-zinc-500 light:text-zinc-400">
                  {periodLabel(i, football)}
                </span>
              ))}
              <span className="w-9 text-right text-[10px] font-semibold uppercase tracking-wider text-zinc-500 light:text-zinc-400">T</span>
            </div>
          )}
          {teams.map((t) => {
            const hasBall = g.state === "in" && g.possessionAbbr === t.abbr;
            return (
              <div key={t.abbr} className="flex items-center gap-2 px-3 py-1.5">
                <TeamMark logo={t.logo} abbr={t.abbr} size={22} />
                <span className="flex min-w-0 items-center gap-1.5 text-sm font-semibold text-zinc-100 light:text-zinc-900">
                  {t.abbr}
                  {hasBall && (football ? <BallIcon size={16} /> : <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400 light:bg-amber-600" aria-label="Possession" />)}
                  {t.record && <span className="truncate text-[11px] font-normal text-zinc-500 light:text-zinc-400">{t.record}</span>}
                </span>
                <span className="ml-auto flex items-baseline">
                  {t.lines.map((ls, i) => (
                    <span key={i} className="tnum hidden w-7 text-right font-mono text-xs text-zinc-400 sm:inline-block light:text-zinc-500">
                      {ls}
                    </span>
                  ))}
                  <span className="tnum w-9 text-right font-mono text-sm font-bold text-white light:text-zinc-900">{t.score}</span>
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </button>
  );
}

interface LinescoreTeam {
  abbr: string;
  name: string;
  logo: string;
  record: string;
  lines: string[];
  total: string;
}

/** Gamecast-style linescore table: team rows × period columns + total.
 * The team in possession gets the same football marker the scoreboard
 * rows use (an amber dot for non-football leagues). */
function LinescoreTable({ teams, periods, football, possessionAbbr }: { teams: LinescoreTeam[]; periods: number; football: boolean; possessionAbbr?: string | null }) {
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="border-b border-white/10 light:border-zinc-200">
          <th className="pb-2 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400 light:text-zinc-500">Team</th>
          {Array.from({ length: periods }, (_, i) => (
            <th key={i} className="tnum hidden w-9 pb-2 text-right font-mono text-[11px] font-semibold uppercase tracking-wider text-zinc-400 sm:table-cell light:text-zinc-500">
              {periodLabel(i, football)}
            </th>
          ))}
          <th className="tnum w-12 pb-2 text-right font-mono text-[11px] font-semibold uppercase tracking-wider text-zinc-300 light:text-zinc-600">T</th>
        </tr>
      </thead>
      <tbody>
        {teams.map((t) => (
          <tr key={t.abbr} className="border-b border-white/5 last:border-0 light:border-zinc-100">
            <td className="py-2.5 pr-2">
              <div className="flex min-w-0 items-center gap-2.5">
                <TeamMark logo={t.logo} abbr={t.abbr} size={30} />
                <span className="truncate text-sm font-bold text-white light:text-zinc-900 sm:text-base">{t.name}</span>
                {possessionAbbr === t.abbr &&
                  (football ? (
                    <BallIcon size={20} />
                  ) : (
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400 light:bg-amber-600" aria-label="Possession" />
                  ))}
                {t.record && <span className="hidden shrink-0 text-xs text-zinc-500 md:inline light:text-zinc-400">{t.record}</span>}
              </div>
            </td>
            {Array.from({ length: periods }, (_, i) => (
              <td key={i} className="tnum hidden w-9 py-2.5 text-right align-middle font-mono text-sm text-zinc-300 sm:table-cell light:text-zinc-600">
                {t.lines[i] ?? "–"}
              </td>
            ))}
            <td className="tnum w-12 py-2.5 text-right align-middle font-display text-2xl font-semibold text-white light:text-zinc-900">
              {t.total}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PlayRow({ p, homeAbbr }: { p: GameDetail["drives"][number]["plays"][number]; homeAbbr: string }) {
  return (
    <div
      className={`flex gap-4 border-b border-white/10 px-5 py-3.5 last:border-0 light:border-zinc-100 ${
        p.scoringPlay ? "border-l-2 border-l-amber-400 bg-amber-400/[0.07]" : ""
      }`}
    >
      <div className="w-[72px] shrink-0 pt-0.5">
        <div className="tnum font-mono text-xs font-bold text-zinc-200 light:text-zinc-800">
          Q{p.period || "–"}
        </div>
        <div className="tnum font-mono text-xs text-zinc-400 light:text-zinc-500">{p.clock}</div>
      </div>
      <div className="min-w-0 flex-1">
        <p className={`text-sm leading-relaxed ${p.scoringPlay ? "font-semibold text-amber-100 light:text-amber-800" : "text-zinc-100 light:text-zinc-900"}`}>
          {p.scoringPlay && <span className="mr-1.5">🏈</span>}
          {p.turnover && !p.scoringPlay && <span className="mr-1.5">🔄</span>}
          {p.text}
        </p>
        {p.downDistance && (
          <p className="mt-1 font-mono text-[11px] uppercase tracking-wide text-zinc-400 light:text-zinc-500">{p.downDistance}</p>
        )}
      </div>
      <div className="tnum shrink-0 pt-0.5 font-mono text-xs font-semibold text-zinc-300 light:text-zinc-600">
        {p.awayScore}–{p.homeScore}
      </div>
    </div>
  );
}

function DriveCard({ dr, isCurrent, homeAbbr, defaultOpen }: { dr: GameDetail["drives"][number]; isCurrent: boolean; homeAbbr: string; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="overflow-hidden rounded-2xl border border-white/15 bg-zinc-900/70 light:border-zinc-200 light:bg-white">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className={`flex w-full items-center justify-between gap-3 bg-zinc-950/70 px-5 py-3 text-left light:bg-zinc-50 ${open ? "border-b border-white/10 light:border-zinc-200" : ""}`}
      >
        <div className="flex min-w-0 items-center gap-2.5">
          <TeamMark logo={dr.teamLogo} abbr={dr.teamAbbr} size={24} />
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold">{dr.description || `${dr.teamAbbr} drive`}</div>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {isCurrent && (
            <span className="rounded bg-amber-400/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-300 light:text-amber-700">
              current
            </span>
          )}
          {dr.result && (
            <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${dr.isScore ? "bg-emerald-400/15 text-emerald-300 light:text-emerald-700" : "bg-zinc-800 text-zinc-400 light:bg-zinc-200 light:text-zinc-600"}`}>
              {dr.result}
            </span>
          )}
          <CollapsePill open={open} />
        </div>
      </button>
      <CollapseRegion open={open}>
        <div>
          {dr.plays.map((p) => (
            <PlayRow key={p.id} p={p} homeAbbr={homeAbbr} />
          ))}
        </div>
      </CollapseRegion>
    </section>
  );
}

function DrivesSection({ detail }: { detail: GameDetail }) {
  if (detail.drives.length === 0) {
    return <p className="mt-3 text-sm text-zinc-400 light:text-zinc-600">No drives yet — the game hasn&apos;t started.</p>;
  }
  return (
    <div className="mt-4 space-y-4">
      {detail.drives.map((dr, di) => (
        <DriveCard key={dr.id} dr={dr} isCurrent={di === 0 && detail.game.state === "in"} homeAbbr={detail.game.homeAbbr} defaultOpen={di === 0} />
      ))}
    </div>
  );
}

function ScoringSection({ detail, football }: { detail: GameDetail; football: boolean }) {
  const [open, setOpen] = useState(true);
  const logoFor = (abbr: string) =>
    abbr === detail.game.awayAbbr ? detail.game.awayLogo : abbr === detail.game.homeAbbr ? detail.game.homeLogo : "";
  return (
    <div className="mt-4 overflow-hidden rounded-2xl border border-white/15 bg-zinc-900/70 light:border-zinc-200 light:bg-white">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className={`flex w-full items-center justify-between gap-3 bg-zinc-950/70 px-5 py-3 text-left light:bg-zinc-50 ${open ? "border-b border-white/10 light:border-zinc-200" : ""}`}
      >
        <span className="text-sm font-semibold">Scoring summary</span>
        <span className="flex shrink-0 items-center gap-2">
          <span className="text-[11px] font-medium text-zinc-400 light:text-zinc-500">
            {detail.scoringPlays.length} {detail.scoringPlays.length === 1 ? "score" : "scores"}
          </span>
          <CollapsePill open={open} />
        </span>
      </button>
      <CollapseRegion open={open}>
      <div>
      {detail.scoringPlays.map((p) => (
        <div key={p.id} className="flex gap-4 border-b border-white/10 px-5 py-3.5 last:border-0 light:border-zinc-100">
          <div className="w-[72px] shrink-0 pt-0.5">
            <div className="tnum font-mono text-xs font-bold text-zinc-200 light:text-zinc-800">
              {p.period ? (football ? `Q${p.period}` : `P${p.period}`) : "–"}
            </div>
            <div className="tnum font-mono text-xs text-zinc-400 light:text-zinc-500">{p.clock}</div>
          </div>
          <TeamMark logo={logoFor(p.teamAbbr)} abbr={p.teamAbbr} size={24} />
          <p className="min-w-0 flex-1 text-sm font-medium leading-relaxed text-zinc-100 light:text-zinc-900">{p.text}</p>
          <div className="tnum shrink-0 pt-0.5 font-mono text-xs font-semibold text-zinc-300 light:text-zinc-600">
            {p.awayScore}–{p.homeScore}
          </div>
        </div>
      ))}
      </div>
      </CollapseRegion>
    </div>
  );
}

function LeaderCard({ tl, logo, hasBall }: { tl: GameDetail["leaders"][number]; logo: string; hasBall: boolean }) {
  const [open, setOpen] = useState(true);
  return (
    <section className="rounded-2xl border border-white/15 bg-zinc-900/70 p-5 light:border-zinc-200 light:bg-white">
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-center gap-2 text-left">
        <TeamMark logo={logo} abbr={tl.teamAbbr} size={24} />
        <h3 className="flex-1 text-sm font-bold text-white light:text-zinc-900">{tl.teamAbbr} leaders</h3>
        {hasBall && <BallIcon size={16} />}
        <CollapsePill open={open} />
      </button>
      <CollapseRegion open={open}>
        <dl className="mt-3 space-y-2.5">
          {tl.leaders.map((l) => (
            <div key={l.category} className="flex items-baseline justify-between gap-3">
              <dt className="shrink-0 text-[11px] font-semibold uppercase tracking-wider text-zinc-400 light:text-zinc-500">{l.category}</dt>
              <dd className="tnum min-w-0 text-right text-sm text-zinc-200 light:text-zinc-800">
                <span className="font-semibold">{l.player}</span>
                {l.value && <span className="ml-1.5 font-mono text-xs text-zinc-400 light:text-zinc-500">{l.value}</span>}
              </dd>
            </div>
          ))}
        </dl>
      </CollapseRegion>
    </section>
  );
}

function StatsSection({ detail, possessionAbbr }: { detail: GameDetail; possessionAbbr: string | null }) {
  const [statsOpen, setStatsOpen] = useState(true);
  const logoFor = (abbr: string) =>
    abbr === detail.game.awayAbbr ? detail.game.awayLogo : abbr === detail.game.homeAbbr ? detail.game.homeLogo : "";
  return (
    <div className="mt-4 grid items-start gap-4 lg:grid-cols-[1fr_320px]">
      {detail.teamStats.length > 0 && (
        <section className="overflow-hidden rounded-2xl border border-white/15 bg-zinc-900/70 light:border-zinc-200 light:bg-white">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/10 bg-zinc-950/70 light:border-zinc-200 light:bg-zinc-50">
                <th className="px-5 py-3 text-left">
                  <span className="flex items-center gap-2 text-sm font-bold text-white light:text-zinc-900">
                    <TeamMark logo={detail.game.awayLogo} abbr={detail.game.awayAbbr} size={22} />
                    {detail.game.awayAbbr}
                    {possessionAbbr === detail.game.awayAbbr && <BallIcon size={16} />}
                  </span>
                </th>
                <th className="px-2 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-zinc-400 light:text-zinc-500">
                  <button onClick={() => setStatsOpen(!statsOpen)} aria-expanded={statsOpen} className="inline-flex items-center gap-1 uppercase tracking-wider">
                    Team stats
                    <CollapsePill open={statsOpen} />
                  </button>
                </th>
                <th className="px-5 py-3 text-right">
                  <span className="flex items-center justify-end gap-2 text-sm font-bold text-white light:text-zinc-900">
                    {detail.game.homeAbbr}
                    {possessionAbbr === detail.game.homeAbbr && <BallIcon size={16} />}
                    <TeamMark logo={detail.game.homeLogo} abbr={detail.game.homeAbbr} size={22} />
                  </span>
                </th>
              </tr>
            </thead>
            {statsOpen && (
              <tbody>
                {detail.teamStats.map((r) => (
                  <tr key={r.label} className="border-b border-white/5 last:border-0 light:border-zinc-100">
                    <td className="tnum px-5 py-2.5 font-mono text-sm font-semibold text-zinc-100 light:text-zinc-900">{r.awayValue || "–"}</td>
                    <td className="px-2 py-2.5 text-center text-xs text-zinc-400 light:text-zinc-500">{r.label}</td>
                    <td className="tnum px-5 py-2.5 text-right font-mono text-sm font-semibold text-zinc-100 light:text-zinc-900">{r.homeValue || "–"}</td>
                  </tr>
                ))}
              </tbody>
            )}
          </table>
        </section>
      )}
      {detail.leaders.length > 0 && (
        <div className="space-y-4">
          {detail.leaders.map((tl) => (
            <LeaderCard key={tl.teamAbbr} tl={tl} logo={logoFor(tl.teamAbbr)} hasBall={possessionAbbr === tl.teamAbbr} />
          ))}
        </div>
      )}
    </div>
  );
}

type TabId = "plays" | "scoring" | "stats";

export default function LivePage({ league = "nfl" as League, basePath = "" }: { league?: League; basePath?: string }) {
  const [games, setGames] = useState<LiveGame[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<GameDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [tab, setTab] = useState<TabId>("plays");
  const [cardOpen, setCardOpen] = useState(true);
  const [listOpen, setListOpen] = useState(true);
  const football = league === "nfl" || league === "college-football";

  const loadBoard = useCallback(async () => {
    try {
      const gs = await fetchScoreboard(league);
      setGames(gs);
      setError(null);
      setSelectedId((prev) => {
        if (prev && gs.some((g) => g.id === prev)) return prev;
        const live = gs.find((g) => g.state === "in");
        return (live ?? gs[0])?.id ?? null;
      });
    } catch {
      setError("Could not reach the live score feed. Try again in a bit.");
    }
  }, [league]);

  const loadDetail = useCallback(async (id: string) => {
    try {
      const d = await fetchGameDetail(league, id);
      setDetail(d);
      setLastUpdate(new Date());
    } catch {
      /* keep previous detail on transient failure */
    }
  }, [league]);

  useEffect(() => {
    loadBoard();
    const t = setInterval(loadBoard, 60000);
    return () => clearInterval(t);
  }, [loadBoard]);

  useEffect(() => {
    if (!selectedId) return;
    setDetail(null);
    setTab("plays");
    loadDetail(selectedId);
    const t = setInterval(() => loadDetail(selectedId), 30000);
    return () => clearInterval(t);
  }, [selectedId, loadDetail]);

  const sorted = useMemo(() => {
    if (!games) return [];
    const rank = { in: 0, post: 1, pre: 2 } as const;
    return [...games].sort((a, b) => rank[a.state] - rank[b.state]);
  }, [games]);
  const liveCount = games?.filter((g) => g.state === "in").length ?? 0;
  const boardGame = games?.find((g) => g.id === selectedId) ?? null;
  // Possession for the selected game, with fallbacks: the summary feed's
  // situation object sometimes comes back empty (breaks, post-score
  // transitions), so fall back to the scoreboard's possession, then the
  // current drive's team.
  const possessionAbbr =
    detail && detail.game.state === "in"
      ? (detail.game.possessionAbbr ??
        boardGame?.possessionAbbr ??
        (detail.drives[0]?.isCurrent ? detail.drives[0].teamAbbr : null))
      : null;

  // Tabs degrade with the feed: basketball summaries carry no drives, and a
  // pre-game feed has nothing yet — show only tabs that have content.
  const tabs: { id: TabId; label: string }[] = detail
    ? [
        ...(detail.drives.length > 0 ? [{ id: "plays" as TabId, label: "Play-by-Play" }] : []),
        ...(detail.scoringPlays.length > 0 ? [{ id: "scoring" as TabId, label: "Scoring Summary" }] : []),
        ...(detail.teamStats.length > 0 || detail.leaders.length > 0
          ? [{ id: "stats" as TabId, label: "Team Stats" }]
          : []),
      ]
    : [];
  const activeTab: TabId | null = tabs.some((t) => t.id === tab) ? tab : (tabs[0]?.id ?? null);

  // Linescore + live situation: prefer the detail feed, fall back to the
  // scoreboard row (the summary feed carries no situation object).
  const awayLines = detail
    ? detail.awayLinescores.length > 0
      ? detail.awayLinescores
      : (boardGame?.awayLinescores ?? [])
    : [];
  const homeLines = detail
    ? detail.homeLinescores.length > 0
      ? detail.homeLinescores
      : (boardGame?.homeLinescores ?? [])
    : [];
  const headerPeriods = Math.max(awayLines.length, homeLines.length);
  // Down & distance now lives in exactly one place: the Gamecast strip's
  // Down / Ball-on readout (simplification pass, 2026-10-19). The header
  // keeps only the game status + last-update time.

  return (
    <div>
      <Eyebrow>{liveCount > 0 ? `${liveCount} game${liveCount > 1 ? "s" : ""} live now · auto-refreshes` : "Auto-refreshes during games"}</Eyebrow>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide sm:text-6xl">
        Live <span className="text-amber-400 light:text-amber-500">play-by-play</span>
      </h1>
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-300 light:text-zinc-600">
        Every snap, live from the ESPN feed — refreshed every 30 seconds.
      </p>

      {error && (
        <p className="mt-6 rounded-xl border border-red-400/25 bg-red-400/10 px-4 py-3 text-sm text-red-200 light:border-red-600/30 light:bg-red-600/10 light:text-red-700">
          {error}
        </p>
      )}

      {!games ? (
        <div className="mt-8 space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-zinc-900/60 light:bg-zinc-200" />
          ))}
        </div>
      ) : games.length === 0 ? (
        <p className="mt-8 rounded-xl border border-white/10 bg-zinc-900/40 p-6 text-sm text-zinc-400 light:border-zinc-200 light:bg-zinc-50 light:text-zinc-600">
          No games on the schedule right now. Check back on game day.
        </p>
      ) : (
        <>
{detail && (
            <div className="mt-8">
          {/* Gamecast header: status + live situation over a linescore table */}
          <div className="rounded-2xl border border-white/20 bg-zinc-800/90 p-5 shadow-lg shadow-black/30 light:border-zinc-200 light:bg-white light:shadow-zinc-300/40">
            <div className="flex items-start justify-between gap-3 pb-2">
              <div className="min-w-0">
                <div className={`text-sm font-bold ${detail.game.state === "in" ? "text-amber-300 light:text-amber-600" : "text-zinc-200 light:text-zinc-600"}`}>
                  {detail.game.state === "in" ? detail.game.detail || "Live" : detail.game.state === "post" ? "Final" : detail.game.detail}
                </div>
                {!cardOpen && (
                  <div className="tnum mt-0.5 font-mono text-sm font-semibold text-zinc-200 light:text-zinc-800">
                    {detail.game.awayAbbr} {detail.game.awayScore} · {detail.game.homeAbbr} {detail.game.homeScore}
                  </div>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {lastUpdate && (
                  <div className="text-[11px] text-zinc-400 light:text-zinc-500">
                    updated {lastUpdate.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" })}
                  </div>
                )}
                <button onClick={() => setCardOpen(!cardOpen)} aria-expanded={cardOpen} aria-label={cardOpen ? "Collapse game card" : "Expand game card"}>
                  <CollapsePill open={cardOpen} />
                </button>
              </div>
            </div>
            <CollapseRegion open={cardOpen}>
            <LinescoreTable
              football={football}
              possessionAbbr={possessionAbbr}
              periods={headerPeriods}
              teams={[
                {
                  abbr: detail.game.awayAbbr,
                  name: detail.game.awayName,
                  logo: boardGame?.awayLogo || detail.game.awayLogo,
                  record: detail.game.awayRecord || boardGame?.awayRecord || "",
                  lines: awayLines,
                  total: detail.game.awayScore,
                },
                {
                  abbr: detail.game.homeAbbr,
                  name: detail.game.homeName,
                  logo: boardGame?.homeLogo || detail.game.homeLogo,
                  record: detail.game.homeRecord || boardGame?.homeRecord || "",
                  lines: homeLines,
                  total: detail.game.homeScore,
                },
              ]}
            />
            {football && <GamecastStrip detail={detail} />}
            </CollapseRegion>
          </div>
          <div className="mt-4">
            <WinProbChart points={detail.winProb} homeAbbr={detail.game.homeAbbr} awayAbbr={detail.game.awayAbbr} />
          </div>
            </div>
          )}

          <div className={`${detail ? "mt-4" : "mt-8"} overflow-hidden rounded-2xl border border-white/15 bg-zinc-900/70 light:border-zinc-200 light:bg-white`}>
            <button
              onClick={() => setListOpen(!listOpen)}
              aria-expanded={listOpen}
              className={`flex w-full items-center justify-between gap-3 bg-zinc-950/70 px-5 py-3 text-left light:bg-zinc-50 ${listOpen ? "border-b border-white/10 light:border-zinc-200" : ""}`}
            >
              <span className="text-sm font-semibold">All games</span>
              <span className="flex shrink-0 items-center gap-2">
                <span className="text-[11px] font-medium text-zinc-400 light:text-zinc-500">
                  {sorted.length} {sorted.length === 1 ? "game" : "games"}
                </span>
                <CollapsePill open={listOpen} />
              </span>
            </button>
            <CollapseRegion open={listOpen}>
              <div className="divide-y divide-white/10 light:divide-zinc-100">
                {sorted.map((g) => (
                  <ScoreboardRow
                    key={g.id}
                    // The selected game's row borrows the detail-derived
                    // possession: both ESPN feeds drop their situation
                    // object during breaks, which blanked the row's icon
                    // at halftime while the card still showed it.
                    g={g.id === selectedId && possessionAbbr ? { ...g, possessionAbbr } : g}
                    selected={g.id === selectedId}
                    onSelect={() => setSelectedId(g.id)}
                    football={football}
                  />
                ))}
              </div>
            </CollapseRegion>
          </div>

          {detail ? (
            <div className="mt-6">
              {/* Tabs: play-by-play / scoring summary / team stats */}
              {tabs.length > 0 && activeTab ? (
                <>
                  <div className="mt-8 flex gap-1 overflow-x-auto border-b border-white/10 light:border-zinc-200" role="tablist" aria-label="Game detail sections">
                    {tabs.map((t) => (
                      <button
                        key={t.id}
                        role="tab"
                        aria-selected={activeTab === t.id}
                        onClick={() => setTab(t.id)}
                        className={`-mb-px shrink-0 border-b-2 px-4 py-2.5 text-sm font-semibold transition ${
                          activeTab === t.id
                            ? "border-amber-400 text-amber-300 light:border-amber-600 light:text-amber-700"
                            : "border-transparent text-zinc-400 hover:text-zinc-200 light:text-zinc-500 light:hover:text-zinc-800"
                        }`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                  {activeTab === "plays" && <DrivesSection detail={detail} />}
                  {activeTab === "scoring" && <ScoringSection detail={detail} football={football} />}
                  {activeTab === "stats" && <StatsSection detail={detail} possessionAbbr={possessionAbbr} />}
                </>
              ) : (
                detail.game.state === "pre" && (
                  <p className="mt-8 text-sm text-zinc-400 light:text-zinc-600">
                    Play-by-play, scoring summary, and team stats appear here once the game is underway.
                  </p>
                )
              )}
            </div>
          ) : (
            selectedId && (
              <div className="mt-6 h-64 animate-pulse rounded-2xl bg-zinc-900/60 light:bg-zinc-200" />
            )
          )}
        </>
      )}

      <p className="mt-8 max-w-2xl text-xs leading-relaxed text-zinc-500 light:text-zinc-500">
        Live data via ESPN · refreshes automatically during games.
      </p>
    </div>
  );
}
