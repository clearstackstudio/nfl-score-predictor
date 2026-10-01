/** Spread helpers. Internally spreads are home margins (positive = home favored). */

export function trim(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1).replace(/\.0$/, "");
}

/** "BAL -11.5" style: favorite-centric, standard sportsbook format. */
export function fmtSpread(homeMargin: number, homeAbbr: string, awayAbbr: string): string {
  if (Math.abs(homeMargin) < 0.05) return "Pick'em";
  if (homeMargin > 0) return `${homeAbbr} -${trim(homeMargin)}`;
  return `${awayAbbr} -${trim(-homeMargin)}`;
}

/** "Over 47.5" / "Under 38.5". */
export function fmtTotal(total: number): string {
  return trim(total);
}

export function fmtPct(p: number | null): string {
  return p == null ? "—" : `${Math.round(p * 100)}%`;
}
