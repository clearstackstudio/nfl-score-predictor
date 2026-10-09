import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "College football pick'em game",
  description:
    "Free college football pick'em game: pick every FBS winner against the spread all season. No account needed.",
  alternates: { canonical: "/cfb/pick-em" },
};

export default function CfbPickEmLayout({ children }: { children: React.ReactNode }) {
  return children;
}
