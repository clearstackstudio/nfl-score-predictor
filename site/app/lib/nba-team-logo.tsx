"use client";

import { useState } from "react";

function initials(name: string): string {
  const words = name.replace(/^(The) /i, "").split(/\s+/);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}

/** ESPN CDN logo codes by canonical full team name. The NBA data files
 * store full names in their abbr fields, so without this map the logo URL
 * was built from e.g. "Boston Celtics" and 404'd — every logo silently
 * fell back to initials. All 30 codes verified live on 2026-10-20. */
const TEAM_CODES: Record<string, string> = {
  "Atlanta Hawks": "atl",
  "Boston Celtics": "bos",
  "Brooklyn Nets": "bkn",
  "Charlotte Hornets": "cha",
  "Chicago Bulls": "chi",
  "Cleveland Cavaliers": "cle",
  "Dallas Mavericks": "dal",
  "Denver Nuggets": "den",
  "Detroit Pistons": "det",
  "Golden State Warriors": "gs",
  "Houston Rockets": "hou",
  "Indiana Pacers": "ind",
  "Los Angeles Clippers": "lac",
  "Los Angeles Lakers": "lal",
  "Memphis Grizzlies": "mem",
  "Miami Heat": "mia",
  "Milwaukee Bucks": "mil",
  "Minnesota Timberwolves": "min",
  "New Orleans Pelicans": "no",
  "New York Knicks": "ny",
  "Oklahoma City Thunder": "okc",
  "Orlando Magic": "orl",
  "Philadelphia 76ers": "phi",
  "Phoenix Suns": "phx",
  "Portland Trail Blazers": "por",
  "Sacramento Kings": "sac",
  "San Antonio Spurs": "sa",
  "Toronto Raptors": "tor",
  "Utah Jazz": "utah",
  "Washington Wizards": "was",
};

function logoCode(abbr: string, name?: string): string {
  return TEAM_CODES[abbr] ?? (name ? TEAM_CODES[name] : undefined) ?? abbr.toLowerCase();
}

/** NBA team badge: ESPN's CDN logo, falls back to initials if it fails. */
export default function NbaTeamLogo({
  abbr,
  name,
  size = 26,
}: {
  abbr: string;
  name?: string;
  size?: number;
}) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <span
        aria-hidden="true"
        className="inline-flex shrink-0 items-center justify-center rounded-full bg-amber-400/15 font-display text-[11px] font-bold text-amber-300 light:bg-amber-600/15 light:text-amber-700"
        style={{ width: size, height: size }}
      >
        {initials(name ?? abbr)}
      </span>
    );
  }
  return (
    <img
      src={`https://a.espncdn.com/i/teamlogos/nba/500/${logoCode(abbr, name)}.png`}
      alt={`${name ?? abbr} logo`}
      width={size}
      height={size}
      className="inline-block shrink-0"
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
