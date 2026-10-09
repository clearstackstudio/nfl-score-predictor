import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NFL pick'em game",
  description:
    "Free NFL pick'em game: pick every winner against the spread and track your record all season. No account needed.",
  alternates: { canonical: "/pick-em" },
};

export default function PickEmLayout({ children }: { children: React.ReactNode }) {
  return children;
}
