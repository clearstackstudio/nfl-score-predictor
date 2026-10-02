import type { Metadata } from "next";
import LivePage from "../../live/page";

export const metadata: Metadata = {
  title: "Honest Line CFB — Live college football play-by-play",
  description:
    "Live college football play-by-play: every snap as it happens, with win probability and drives.",
};

export default function CfbLivePage() {
  return <LivePage league="college-football" />;
}
