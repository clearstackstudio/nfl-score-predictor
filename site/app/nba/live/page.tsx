import type { Metadata } from "next";
import LivePage from "../../live/page";

export const metadata: Metadata = {
  title: "NBA live play-by-play",
  description:
    "Live NBA play-by-play: every possession as it happens, with win probability.",
  alternates: { canonical: "/nba/live" },
};

export default function NbaLivePage() {
  return <LivePage league="nba" />;
}
