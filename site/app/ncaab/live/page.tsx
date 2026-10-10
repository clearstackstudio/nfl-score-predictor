import type { Metadata } from "next";
import LivePage from "../../live/page";

export const metadata: Metadata = {
  title: "NCAAB live play-by-play",
  description:
    "Live NCAAB play-by-play: every possession as it happens, with win probability.",
  alternates: { canonical: "/ncaab/live" },
};

export default function NcaabLivePage() {
  return <LivePage league="mens-college-basketball" />;
}
