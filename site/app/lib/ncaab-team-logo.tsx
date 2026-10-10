"use client";

/**
 * NCAAB team badge. The pipeline stores canonical CBBD team names
 * (e.g. "Duke"), and ESPN's college-logo CDN is keyed by numeric team ID,
 * not name — so we render a clean initials badge instead of guessing URLs.
 */
function initials(name: string): string {
  const words = name.replace(/^(The) /i, "").split(/\s+/);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}

export default function NcaabTeamLogo({
  abbr,
  name,
  size = 26,
}: {
  abbr: string;
  name?: string;
  size?: number;
}) {
  return (
    <span
      aria-hidden="true"
      title={name ?? abbr}
      className="inline-flex shrink-0 items-center justify-center rounded-full bg-amber-400/15 font-display text-[11px] font-bold text-amber-300 light:bg-amber-600/15 light:text-amber-700"
      style={{ width: size, height: size }}
    >
      {initials(name ?? abbr)}
    </span>
  );
}
