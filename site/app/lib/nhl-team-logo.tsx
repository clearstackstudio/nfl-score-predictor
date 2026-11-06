"use client";

import { useState } from "react";

function initials(name: string): string {
  const words = name.replace(/^(The) /i, "").split(/\s+/);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}

/** ESPN CDN logo codes by NHL abbreviation. The NHL data files store
 * real abbreviations (BUF, MTL, …), but several differ from ESPN's
 * codes (LAK→la, MTL→mon, NJD→nj, SJS→sj, TBL→tb, UTA→utah), so the
 * map is explicit for all 32 teams; anything unmapped falls back to
 * the lowercased abbreviation, then to initials if the image fails. */
const TEAM_CODES: Record<string, string> = {
  ANA: "ana", BOS: "bos", BUF: "buf", CGY: "cgy", CAR: "car",
  CHI: "chi", COL: "col", CBJ: "cbj", DAL: "dal", DET: "det",
  EDM: "edm", FLA: "fla", LAK: "la", MIN: "min", MTL: "mon",
  NSH: "nsh", NJD: "nj", NYI: "nyi", NYR: "nyr", OTT: "ott",
  PHI: "phi", PIT: "pit", SJS: "sj", SEA: "sea", STL: "stl",
  TBL: "tb", TOR: "tor", UTA: "utah", VAN: "van", VGK: "vgk",
  WSH: "wsh", WPG: "wpg",
};

function logoCode(abbr: string): string {
  return TEAM_CODES[abbr] ?? abbr.toLowerCase();
}

/** NHL team badge: ESPN's CDN logo, falls back to initials if it fails. */
export default function NhlTeamLogo({
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
        className="inline-flex shrink-0 items-center justify-center rounded-full bg-red-500/15 font-display text-[11px] font-bold text-red-300 light:bg-red-600/15 light:text-red-700"
        style={{ width: size, height: size }}
      >
        {initials(name ?? abbr)}
      </span>
    );
  }
  return (
    <img
      src={`https://a.espncdn.com/i/teamlogos/nhl/500/${logoCode(abbr)}.png`}
      alt={`${name ?? abbr} logo`}
      width={size}
      height={size}
      className="inline-block shrink-0"
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
