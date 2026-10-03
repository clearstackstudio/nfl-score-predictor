"use client";

import { useState } from "react";

function initials(name: string): string {
  const words = name.replace(/^(The) /i, "").split(/\s+/);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
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
      src={`https://a.espncdn.com/i/teamlogos/nba/500/${abbr.toLowerCase()}.png`}
      alt={`${name ?? abbr} logo`}
      width={size}
      height={size}
      className="inline-block shrink-0"
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
