"use client";

import { useState } from "react";

export default function SharePicks({ label = "Share this week's picks" }: { label?: string }) {
  const [busy, setBusy] = useState(false);

  const share = async () => {
    setBusy(true);
    try {
      const res = await fetch("/api/pick-slip");
      if (!res.ok) throw new Error("Could not generate image.");
      const blob = await res.blob();
      const file = new File([blob], "honest-line-picks.png", { type: "image/png" });
      // Native share sheet on mobile when supported
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: "Honest Line picks",
          text: "This week's Honest Line model picks — full graded record at honest-line.vercel.app",
        });
      } else {
        // Fallback: download the image
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "honest-line-picks.png";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }
    } catch (e) {
      // User cancelled share — not an error
      if (e instanceof Error && e.name !== "AbortError") console.error(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      onClick={share}
      disabled={busy}
      className="inline-flex items-center gap-2 rounded-full border border-amber-400/40 px-5 py-2.5 text-sm font-semibold text-amber-400 transition hover:bg-amber-400/10 disabled:opacity-50 light:border-amber-600/40 light:text-amber-700 light:hover:bg-amber-600/10"
    >
      <svg aria-hidden="true" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3v9M8 7l4-4 4 4M4 13h12" transform="translate(-2 0)" />
        <path d="M2 12v2h12v-2" />
      </svg>
      {busy ? "Preparing…" : label}
    </button>
  );
}
