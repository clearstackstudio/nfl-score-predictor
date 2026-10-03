import type { Metadata } from "next";
import LivePage from "../../live/page";

export const metadata: Metadata = {
  title: "Honest Line NBA — Live NBA play-by-play",
  description:
    "Live NBA play-by-play: every possession as it happens, with win probability.",
};

export default function NbaLivePage() {
  return <LivePage league="nba" />;
}
