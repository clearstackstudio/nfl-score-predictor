import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NFL live play-by-play",
  description:
    "Live NFL play-by-play: every snap as it happens, with win probability and drives.",
  alternates: { canonical: "/live" },
};

export default function LiveLayout({ children }: { children: React.ReactNode }) {
  return children;
}
