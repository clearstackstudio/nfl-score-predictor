import type { Metadata } from "next";
import LivePage from "../../live/page";

export const metadata: Metadata = {
  title: "College football live play-by-play",
  description:
    "Live college football play-by-play: every snap as it happens, with win probability and drives.",
  alternates: { canonical: "/cfb/live" },
};

export default function CfbLivePage() {
  return <LivePage league="college-football" />;
}
