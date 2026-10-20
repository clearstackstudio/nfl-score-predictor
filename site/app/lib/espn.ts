// ESPN unofficial API helpers (site.api.espn.com). Free, no key, CORS-open.
// Used for live scores + play-by-play. Falls back gracefully when no games live.

export type League = "nfl" | "college-football" | "nba" | "mens-college-basketball";

function sportOf(l: League): "football" | "basketball" {
  return l === "nfl" || l === "college-football" ? "football" : "basketball";
}

export type GameState = "pre" | "in" | "post";

export interface LiveGame {
  id: string;
  name: string;
  shortName: string;
  date: string;
  state: GameState;
  detail: string;
  awayAbbr: string;
  awayName: string;
  awayScore: string;
  awayLogo: string;
  awayRecord: string;
  awayLinescores: string[];
  homeAbbr: string;
  homeName: string;
  homeScore: string;
  homeLogo: string;
  homeRecord: string;
  homeLinescores: string[];
  /** Abbreviation of the team currently in possession, or null if unknown/not live. */
  possessionAbbr: string | null;
  /** Live down & distance text, e.g. "1st & 10 at DEN 34", or null when not live/unknown. */
  situationText: string | null;
  /** Team brand colors (hex, no '#') for the Gamecast end zones — detail feed only. */
  awayColor?: string;
  homeColor?: string;
  awayAltColor?: string;
  homeAltColor?: string;
}

export interface StatRow {
  label: string;
  awayValue: string;
  homeValue: string;
}

export interface TeamLeader {
  category: string;
  player: string;
  value: string;
}

export interface TeamLeaders {
  teamAbbr: string;
  leaders: TeamLeader[];
}

export interface ScoringPlay {
  id: string;
  period: number;
  clock: string;
  teamAbbr: string;
  text: string;
  awayScore: number;
  homeScore: number;
}

export interface PlaySpot {
  /** Absolute field position, 0–100 (one goal line to the other). */
  yardLine: number;
  yardsToEndzone: number;
  down: number;
  distance: number;
  /** Territory text, e.g. "WSH 1". */
  text: string;
  /** Full situation text, e.g. "3rd & Goal at WSH 1". */
  downDistanceText: string;
}

export interface Play {
  id: string;
  text: string;
  period: number;
  clock: string;
  awayScore: number;
  homeScore: number;
  scoringPlay: boolean;
  turnover: boolean;
  downDistance?: string;
  /** Play type label from the feed, e.g. "Sack", "Pass", "Rush". */
  typeText?: string;
  /** This play's pre-snap situation, e.g. "3rd & 9 at WSH 44". */
  startText?: string;
  /** Where the ball sits for the next snap (this play's end state, falling
   * back to its start) — the Gamecast field position. */
  spot?: PlaySpot;
}

export interface Drive {
  id: string;
  teamAbbr: string;
  teamLogo: string;
  description: string;
  result: string;
  isScore: boolean;
  /** True for the drive in progress (ESPN's drives.current), false for completed ones. */
  isCurrent: boolean;
  plays: Play[]; // newest first
}

export interface WinProbPoint {
  homeWinPct: number;
  playId: string;
}

export interface GameDetail {
  game: LiveGame;
  drives: Drive[];
  winProb: WinProbPoint[];
  awayLinescores: string[];
  homeLinescores: string[];
  teamStats: StatRow[];
  leaders: TeamLeaders[];
  scoringPlays: ScoringPlay[];
}

interface RawLinescore {
  value?: number | null;
  displayValue?: string;
}

interface RawTeamExtras {
  records?: { summary?: string }[];
  linescores?: RawLinescore[];
}

/** Period scores from a scoreboard competitor: linescores carry a numeric value. */
function boardLinescores(c: RawTeamExtras | undefined): string[] {
  return (c?.linescores ?? [])
    .map((l) => (l?.value != null ? String(Math.trunc(Number(l.value))) : l?.displayValue ?? ""))
    .filter((s) => s !== "");
}

/** Period scores from a summary competitor: value is null there, displayValue is set. */
function summaryLinescores(c: RawTeamExtras | undefined): string[] {
  return (c?.linescores ?? [])
    .map((l) => l?.displayValue ?? (l?.value != null ? String(Math.trunc(Number(l.value))) : ""))
    .filter((s) => s !== "");
}

function recordOf(c: RawTeamExtras | undefined): string {
  return c?.records?.[0]?.summary ?? "";
}

interface RawStatTeam {
  homeAway?: string;
  statistics?: { label?: string; displayValue?: string }[];
}

interface RawLeaderTeam {
  team?: { abbreviation?: string };
  leaders?: {
    displayName?: string;
    leaders?: { athlete?: { displayName?: string }; displayValue?: string }[];
  }[];
}

interface RawScoringPlay {
  id?: string | number;
  period?: { number?: number };
  clock?: { displayValue?: string };
  team?: { abbreviation?: string };
  text?: string;
  awayScore?: number;
  homeScore?: number;
}

const API = "https://site.api.espn.com/apis/site/v2/sports";

function stateOf(s: string): GameState {
  return s === "in" ? "in" : s === "post" ? "post" : "pre";
}

export async function fetchScoreboard(league: League): Promise<LiveGame[]> {
  const res = await fetch(`${API}/${sportOf(league)}/${league}/scoreboard`, { cache: "no-store" });
  if (!res.ok) throw new Error(`scoreboard ${res.status}`);
  const d = await res.json();
  return (d.events ?? []).map((ev: any): LiveGame => {
    const comp = ev.competitions?.[0] ?? {};
    const away = comp.competitors?.find((c: any) => c.homeAway === "away") ?? {};
    const home = comp.competitors?.find((c: any) => c.homeAway === "home") ?? {};
    // ESPN reports possession as a team id in the live situation; map it to an abbreviation
    const possId = comp.situation?.possession;
    const possessionAbbr =
      possId != null && String(away.team?.id) === String(possId)
        ? (away.team?.abbreviation ?? null)
        : possId != null && String(home.team?.id) === String(possId)
          ? (home.team?.abbreviation ?? null)
          : null;
    return {
      id: ev.id,
      name: ev.name,
      shortName: ev.shortName,
      date: ev.date,
      state: stateOf(comp.status?.type?.state ?? "pre"),
      detail: comp.status?.type?.shortDetail ?? "",
      awayAbbr: away.team?.abbreviation ?? "",
      awayName: away.team?.displayName ?? away.team?.abbreviation ?? "",
      awayScore: away.score ?? "0",
      awayLogo: away.team?.logo ?? "",
      awayRecord: recordOf(away),
      awayLinescores: boardLinescores(away),
      homeAbbr: home.team?.abbreviation ?? "",
      homeName: home.team?.displayName ?? home.team?.abbreviation ?? "",
      homeScore: home.score ?? "0",
      homeLogo: home.team?.logo ?? "",
      homeRecord: recordOf(home),
      homeLinescores: boardLinescores(home),
      possessionAbbr,
      situationText: comp.situation?.downDistanceText ?? null,
    };
  });
}

function spotOf(s: any): PlaySpot | undefined {
  // A real scrimmage state only: administrative entries (timeouts, quarter
  // breaks) and drive-ending plays carry down -1/0 and no trustworthy spot.
  if (!s || typeof s.yardLine !== "number" || !(s.down >= 1)) return undefined;
  return {
    yardLine: s.yardLine,
    yardsToEndzone: typeof s.yardsToEndzone === "number" ? s.yardsToEndzone : 100 - s.yardLine,
    down: s.down,
    distance: s.distance ?? 0,
    text: s.possessionText ?? "",
    downDistanceText: s.downDistanceText ?? "",
  };
}

function toPlay(p: any): Play {
  const start = p.start ?? {};
  const down = start.down ?? p.down;
  const dist = start.distance ?? p.distance;
  return {
    id: String(p.id),
    text: p.text ?? "",
    period: p.period?.number ?? 0,
    clock: p.clock?.displayValue ?? "",
    awayScore: Number(p.awayScore ?? 0),
    homeScore: Number(p.homeScore ?? 0),
    scoringPlay: !!p.scoringPlay,
    turnover: !!p.turnover,
    downDistance:
      down && dist ? `${down}${ordinal(down)} & ${dist}` : undefined,
    typeText: p.type?.text ?? undefined,
    startText: start.downDistanceText ?? undefined,
    // The next snap's state is this play's END; if the play ended the drive
    // (score, turnover, downs), fall back to where the snap itself happened.
    spot: spotOf(p.end) ?? spotOf(p.start),
  };
}

function ordinal(n: number): string {
  return n === 1 ? "st" : n === 2 ? "nd" : n === 3 ? "rd" : "th";
}

export async function fetchGameDetail(league: League, gameId: string): Promise<GameDetail> {
  const res = await fetch(`${API}/${sportOf(league)}/${league}/summary?event=${gameId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`summary ${res.status}`);
  const d = await res.json();
  const comp = d.header?.competitions?.[0] ?? {};
  const away = comp.competitors?.find((c: any) => c.homeAway === "away") ?? {};
  const home = comp.competitors?.find((c: any) => c.homeAway === "home") ?? {};
  const possId = comp.situation?.possession;
  const possessionAbbr =
    possId != null && String(away.team?.id) === String(possId)
      ? (away.team?.abbreviation ?? null)
      : possId != null && String(home.team?.id) === String(possId)
        ? (home.team?.abbreviation ?? null)
        : null;
  const game: LiveGame = {
    id: String(d.header?.id ?? gameId),
    name: d.header?.name ?? "",
    shortName: "",
    date: "",
    state: stateOf(comp.status?.type?.state ?? "pre"),
    detail: comp.status?.type?.shortDetail ?? "",
    awayAbbr: away.team?.abbreviation ?? "",
    awayName: away.team?.displayName ?? "",
    awayScore: away.score ?? "0",
    awayLogo: away.team?.logo ?? "",
    awayRecord: recordOf(away),
    awayLinescores: summaryLinescores(away),
    homeAbbr: home.team?.abbreviation ?? "",
    homeName: home.team?.displayName ?? "",
    homeScore: home.score ?? "0",
    homeLogo: home.team?.logo ?? "",
    homeRecord: recordOf(home),
    homeLinescores: summaryLinescores(home),
    possessionAbbr,
    situationText: comp.situation?.downDistanceText ?? null,
    awayColor: away.team?.color ?? undefined,
    homeColor: home.team?.color ?? undefined,
    awayAltColor: away.team?.alternateColor ?? undefined,
    homeAltColor: home.team?.alternateColor ?? undefined,
  };

  const logoFor = (abbr: string) =>
    abbr === game.awayAbbr ? game.awayLogo : abbr === game.homeAbbr ? game.homeLogo : "";

  const hasCurrent = !!d.drives?.current;
  const rawDrives: any[] = [
    ...(hasCurrent ? [d.drives.current] : []),
    ...(d.drives?.previous ?? []),
  ];
  const drives: Drive[] = rawDrives.map((dr: any, i: number) => {
    const teamAbbr = dr.team?.abbreviation ?? "";
    const plays: Play[] = (dr.plays ?? []).map(toPlay).reverse(); // newest first
    return {
      id: String(dr.id),
      teamAbbr,
      teamLogo: dr.team?.logo ?? logoFor(teamAbbr),
      description: dr.description ?? "",
      result: dr.displayResult ?? dr.shortDisplayResult ?? "",
      isScore: !!dr.isScore,
      isCurrent: hasCurrent && i === 0,
      plays,
    };
  });

  const winProb: WinProbPoint[] = (d.winprobability ?? []).map((w: any) => ({
    homeWinPct: Number(w.homeWinPercentage ?? 0.5),
    playId: String(w.playId ?? ""),
  }));

  // Team stats: align the two boxscore.teams statistics lists by label,
  // preserving the away team's label order, then any home-only labels.
  const statList = (side: "away" | "home"): { label: string; value: string }[] => {
    const t = ((d.boxscore?.teams ?? []) as RawStatTeam[]).find((x) => x?.homeAway === side);
    return (t?.statistics ?? [])
      .map((s) => ({ label: s?.label ?? "", value: s?.displayValue ?? "" }))
      .filter((s) => s.label !== "");
  };
  const awayStats = statList("away");
  const homeStats = statList("home");
  const homeByLabel = new Map(homeStats.map((s) => [s.label, s.value]));
  const teamStats: StatRow[] = awayStats.map((s) => ({
    label: s.label,
    awayValue: s.value,
    homeValue: homeByLabel.get(s.label) ?? "",
  }));
  for (const s of homeStats) {
    if (!teamStats.some((r) => r.label === s.label)) {
      teamStats.push({ label: s.label, awayValue: "", homeValue: s.value });
    }
  }

  // Game leaders per team. ESPN reports the placeholder player name
  // "None" for empty categories (e.g. sacks before any sack) — drop those.
  const leaders: TeamLeaders[] = ((d.leaders ?? []) as RawLeaderTeam[])
    .map((tl): TeamLeaders => {
      const rows: TeamLeader[] = [];
      for (const cat of tl?.leaders ?? []) {
        const top = cat?.leaders?.[0];
        const player = top?.athlete?.displayName ?? "";
        if (!cat?.displayName || !player || player === "None") continue;
        rows.push({ category: cat.displayName, player, value: top?.displayValue ?? "" });
      }
      return { teamAbbr: tl?.team?.abbreviation ?? "", leaders: rows };
    })
    .filter((t: TeamLeaders) => t.teamAbbr !== "" && t.leaders.length > 0);

  const scoringPlays: ScoringPlay[] = ((d.scoringPlays ?? []) as RawScoringPlay[])
    .map((p, i): ScoringPlay => ({
      id: String(p?.id ?? i),
      period: p?.period?.number ?? 0,
      clock: p?.clock?.displayValue ?? "",
      teamAbbr: p?.team?.abbreviation ?? "",
      text: p?.text ?? "",
      awayScore: Number(p?.awayScore ?? 0),
      homeScore: Number(p?.homeScore ?? 0),
    }))
    .filter((p) => p.text !== "");

  return {
    game,
    drives,
    winProb,
    awayLinescores: game.awayLinescores,
    homeLinescores: game.homeLinescores,
    teamStats,
    leaders,
    scoringPlays,
  };
}
