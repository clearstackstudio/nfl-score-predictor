import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NBA pick'em game",
  description:
    "Free NBA pick'em game: pick every winner against the spread all season. No account needed.",
  alternates: { canonical: "/nba/pick-em" },
};

export default function NbaPickEmLayout({ children }: { children: React.ReactNode }) {
  return children;
}
