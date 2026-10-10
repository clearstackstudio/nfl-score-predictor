import type { Metadata } from "next";
import CalibrationPage from "./calibration-page";

export const metadata: Metadata = {
  title: "Calibration",
  description:
    "Do our published probabilities mean what they say? Backtest calibration curves and this season's live receipts for every Honest Line sport.",
  alternates: { canonical: "/calibration" },
};

export default function Calibration() {
  return <CalibrationPage />;
}
