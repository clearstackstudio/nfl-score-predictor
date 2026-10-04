"use client";

export default function TeamLogo({
  abbr,
  size = 24,
}: {
  abbr: string;
  size?: number;
}) {
  return (
    <img
      src={`/logos/${abbr}.png`}
      alt={`${abbr} logo`}
      width={size}
      height={size}
      className="inline-block shrink-0"
      loading="lazy"
      onError={(e) => {
        // Hide gracefully if a logo file is missing instead of showing a broken image
        (e.target as HTMLImageElement).style.display = "none";
      }}
    />
  );
}
