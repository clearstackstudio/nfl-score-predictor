"use client";

import { useState } from "react";

function slug(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function initials(name: string): string {
  const words = name.replace(/^(University of|The) /i, "").split(/\s+/);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}

/** College team badge: tries /logos/cfb/<slug>.png, falls back to initials.
 *  Real logos get downloaded from the CFBD /teams endpoint at data-pull time. */
export default function CfbTeamLogo({ name, size = 26 }: { name: string; size?: number }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <span
        aria-hidden="true"
        className="inline-flex shrink-0 items-center justify-center rounded-full bg-amber-400/15 font-display text-[11px] font-bold text-amber-300 light:bg-amber-600/15 light:text-amber-700"
        style={{ width: size, height: size }}
      >
        {initials(name)}
      </span>
    );
  }
  return (
    <img
      src={`/logos/cfb/${slug(name)}.png`}
      alt={`${name} logo`}
      width={size}
      height={size}
      className="inline-block shrink-0"
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
