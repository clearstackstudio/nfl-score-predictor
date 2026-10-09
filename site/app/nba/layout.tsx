import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    default: "NBA picks",
    template: "%s · Honest Line",
  },
  description:
    "NBA picks from a fundamentals-only model: every game, spreads and totals, published before tip-off.",
  alternates: { canonical: "/nba" },
};

export default function NbaLayout({ children }: { children: React.ReactNode }) {
  return children;
}
