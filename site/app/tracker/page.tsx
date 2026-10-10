import type { Metadata } from "next";
import TrackerPage from "./tracker-page";

export const metadata: Metadata = {
  title: "Bet Tracker",
  description:
    "Log your own bets and get the Honest Line treatment: real record, honest ROI, and a calibration plot of your odds against your actual hit rate. Your receipt, not your memory.",
  alternates: { canonical: "/tracker" },
};

export default function Tracker() {
  return <TrackerPage />;
}
