import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    default: "NHL picks",
    template: "%s · Honest Line",
  },
  description:
    "NHL moneyline picks from an expected-goals model: every game, model probabilities next to the market, published before puck drop and graded in public.",
  alternates: { canonical: "/nhl" },
};

export default function NhlLayout({ children }: { children: React.ReactNode }) {
  return children;
}
