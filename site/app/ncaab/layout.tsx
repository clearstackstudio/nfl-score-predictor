import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    default: "NCAAB picks",
    template: "%s · Honest Line",
  },
  description:
    "NCAAB picks from a fundamentals-only efficiency model: every game, spreads and totals, published before tip-off.",
  alternates: { canonical: "/ncaab" },
};

export default function NcaabLayout({ children }: { children: React.ReactNode }) {
  return children;
}
