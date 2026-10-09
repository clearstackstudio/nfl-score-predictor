import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "MLB picks",
  description:
    "MLB picks from a park-adjusted runs model: moneylines and totals for the 2027 season. Offseason now — full 10-season backtest record inside.",
  alternates: { canonical: "/mlb" },
};

export default function MlbLayout({ children }: { children: React.ReactNode }) {
  return children;
}
