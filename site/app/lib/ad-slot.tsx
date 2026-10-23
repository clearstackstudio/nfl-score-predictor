"use client";

// Ad slots — two states, one reserved box, so layout never shifts (CLS).
//
// Configured state: NEXT_PUBLIC_ADSENSE_ID and the per-format slot id are
// set at build time. The slot loads Google AdSense (script included once
// per page by next/script's src dedupe) and the frame is labeled
// "Advertisement", like ESPN's.
//
// Unconfigured state (today — no AdSense account yet): the same reserved
// box runs a house promo for one of Honest Line's own pages, tagged
// "Honest Line". It is NOT labeled an advertisement and carries no sponsor
// content. Which promo shows is decided deterministically by league +
// format, so every page shows a different one and nothing is random.
//
// Flipping to real ads later is only an env change: set
// NEXT_PUBLIC_ADSENSE_ID (ca-pub-… or pub-…), NEXT_PUBLIC_ADSENSE_SLOT_LEADERBOARD
// and NEXT_PUBLIC_ADSENSE_SLOT_RECTANGLE in Vercel, then redeploy.

import { useEffect } from "react";
import Link from "next/link";
import Script from "next/script";

export type AdLeague = "nfl" | "cfb" | "nba" | "ncaab" | "mlb";
export type AdFormat = "leaderboard" | "rectangle";

const PUBLISHER_ID = process.env.NEXT_PUBLIC_ADSENSE_ID ?? "";
const SLOT_IDS: Record<AdFormat, string> = {
  leaderboard: process.env.NEXT_PUBLIC_ADSENSE_SLOT_LEADERBOARD ?? "",
  rectangle: process.env.NEXT_PUBLIC_ADSENSE_SLOT_RECTANGLE ?? "",
};

function adsenseClient(id: string): string {
  if (!id) return "";
  return id.startsWith("ca-") ? id : `ca-${id}`;
}

declare global {
  interface Window {
    adsbygoogle?: Record<string, unknown>[];
  }
}

type Promo = { headline: string; sub: string; href: string; cta: string };

const LEAGUES: Record<
  AdLeague,
  { label: string; home: string; record: string; pickem: string }
> = {
  nfl: { label: "NFL", home: "/", record: "/track-record", pickem: "/pick-em" },
  cfb: { label: "College football", home: "/cfb", record: "/cfb/track-record", pickem: "/cfb/pick-em" },
  nba: { label: "NBA", home: "/nba", record: "/nba/track-record", pickem: "/nba/pick-em" },
  ncaab: { label: "College hoops", home: "/ncaab", record: "/ncaab/track-record", pickem: "/ncaab/pick-em" },
  mlb: { label: "MLB", home: "/mlb", record: "/mlb/track-record", pickem: "/mlb/pick-em" },
};

const LEAGUE_ORDER: AdLeague[] = ["nfl", "cfb", "nba", "ncaab", "mlb"];

function housePromo(league: AdLeague, format: AdFormat): Promo {
  const me = LEAGUES[league];
  const others = LEAGUE_ORDER.filter((l) => l !== league).map((l) => LEAGUES[l]);
  const catalog: Promo[] = [
    {
      headline: "Play Pick'em",
      sub: `Make your ${me.label} picks against the model and climb the board.`,
      href: me.pickem,
      cta: "Play free",
    },
    {
      headline: "Every pick, graded in public",
      sub: `The full ${me.label} track record — winners, losers, pushes. Nothing hidden.`,
      href: me.record,
      cta: "See the record",
    },
    {
      headline: "Are the percentages honest?",
      sub: "When we say 60%, it should happen 60 times in 100. Check the receipts.",
      href: "/calibration",
      cta: "Calibration page",
    },
    {
      headline: `${others[0].label} picks`,
      sub: `The same public-track-record model, on the ${others[0].label} board.`,
      href: others[0].home,
      cta: "View picks",
    },
    {
      headline: `${others[1].label} picks`,
      sub: "More games, same honesty rules — every result graded in public.",
      href: others[1].home,
      cta: "View picks",
    },
  ];
  const idx = LEAGUE_ORDER.indexOf(league) * 2 + (format === "rectangle" ? 1 : 0);
  return catalog[idx % catalog.length];
}

function HousePromo({
  format,
  league,
  box,
}: {
  format: AdFormat;
  league: AdLeague;
  box: string;
}) {
  const promo = housePromo(league, format);
  const tall = format === "rectangle";
  return (
    <Link
      href={promo.href}
      className={`group relative flex flex-col justify-between overflow-hidden rounded-xl border border-red-500/25 bg-gradient-to-b from-red-500/[0.09] to-red-500/[0.03] p-3.5 transition hover:border-red-500/50 light:border-red-600/30 light:from-red-600/[0.08] light:to-red-600/[0.02] light:hover:border-red-600/50 ${box}`}
    >
      <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-red-500/90 light:text-red-700">
        Honest Line
      </span>
      <span>
        <span
          className={`block font-display font-semibold uppercase leading-tight tracking-wide text-zinc-100 light:text-zinc-900 ${
            tall ? "text-3xl" : "text-2xl sm:text-[28px]"
          }`}
        >
          {promo.headline}
        </span>
        {tall && (
          <span className="mt-2 block text-sm leading-relaxed text-zinc-400 light:text-zinc-600">
            {promo.sub}
          </span>
        )}
        <span className="mt-2 inline-block text-xs font-bold uppercase tracking-wider text-red-300 transition group-hover:text-red-200 light:text-red-700 light:group-hover:text-red-800">
          {promo.cta} →
        </span>
      </span>
    </Link>
  );
}

export default function AdSlot({
  format,
  league = "nfl",
}: {
  format: AdFormat;
  league?: AdLeague;
}) {
  const slotId = SLOT_IDS[format];
  const configured = Boolean(PUBLISHER_ID && slotId);
  const client = adsenseClient(PUBLISHER_ID);

  useEffect(() => {
    if (!configured) return;
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch {
      /* AdSense blocked or unavailable — the reserved box stays empty. */
    }
  }, [configured]);

  // The reserved box: leaderboard is 320x100 on phones, 728x90 from sm up;
  // rectangle is a fixed 300x250. Heights are set in both modes, so the
  // page cannot shift when the env flips or an ad fills.
  const box =
    format === "leaderboard"
      ? "h-[100px] w-full max-w-[728px] sm:h-[90px]"
      : "h-[250px] w-[300px] max-w-full";

  return (
    <div className="my-8 flex flex-col items-center" data-ad-slot={format}>
      {configured ? (
        <>
          <span className="mb-1.5 text-[10px] font-medium uppercase tracking-[0.18em] text-zinc-500">
            Advertisement
          </span>
          <div className={`flex items-start justify-center overflow-hidden ${box}`}>
            <Script
              src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${client}`}
              strategy="afterInteractive"
              crossOrigin="anonymous"
            />
            {format === "leaderboard" ? (
              <ins
                className="adsbygoogle"
                style={{ display: "block", width: "100%", height: "100%" }}
                data-ad-client={client}
                data-ad-slot={slotId}
                data-ad-format="auto"
                data-full-width-responsive="true"
              />
            ) : (
              <ins
                className="adsbygoogle"
                style={{ display: "inline-block", width: 300, height: 250 }}
                data-ad-client={client}
                data-ad-slot={slotId}
              />
            )}
          </div>
        </>
      ) : (
        <HousePromo format={format} league={league} box={box} />
      )}
    </div>
  );
}
