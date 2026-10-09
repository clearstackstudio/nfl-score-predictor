import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "College football picks",
  description:
    "College football picks from a fundamentals-only model: every FBS game, spreads and totals, published before kickoff.",
  alternates: { canonical: "/cfb" },
};

export default function CfbLayout({ children }: { children: React.ReactNode }) {
  return children;
}
