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
  homeAbbr: string;
  homeName: string;
  homeScore: string;
  homeLogo: string;
  /** Abbreviation of the team currently in possession, or null if unknown/not live. */
  possessionAbbr: string | null;
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
}

export interface Drive {
  id: string;
  teamAbbr: string;
  teamLogo: string;
  description: string;
  result: string;
  isScore: boolean;
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
      homeAbbr: home.team?.abbreviation ?? "",
      homeName: home.team?.displayName ?? home.team?.abbreviation ?? "",
      homeScore: home.score ?? "0",
      homeLogo: home.team?.logo ?? "",
      possessionAbbr,
    };
  });
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
    homeAbbr: home.team?.abbreviation ?? "",
    homeName: home.team?.displayName ?? "",
    homeScore: home.score ?? "0",
    homeLogo: home.team?.logo ?? "",
    possessionAbbr,
  };

  const logoFor = (abbr: string) =>
    abbr === game.awayAbbr ? game.awayLogo : abbr === game.homeAbbr ? game.homeLogo : "";

  const rawDrives: any[] = [
    ...(d.drives?.current ? [d.drives.current] : []),
    ...(d.drives?.previous ?? []),
  ];
  const drives: Drive[] = rawDrives.map((dr: any) => {
    const teamAbbr = dr.team?.abbreviation ?? "";
    const plays: Play[] = (dr.plays ?? []).map(toPlay).reverse(); // newest first
    return {
      id: String(dr.id),
      teamAbbr,
      teamLogo: dr.team?.logo ?? logoFor(teamAbbr),
      description: dr.description ?? "",
      result: dr.displayResult ?? dr.shortDisplayResult ?? "",
      isScore: !!dr.isScore,
      plays,
    };
  });

  const winProb: WinProbPoint[] = (d.winprobability ?? []).map((w: any) => ({
    homeWinPct: Number(w.homeWinPercentage ?? 0.5),
    playId: String(w.playId ?? ""),
  }));

  return { game, drives, winProb };
}
