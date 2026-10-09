"use client";

import { useState } from "react";
import SharePreviewDialog, { type SharePreview } from "./share-dialog";

/**
 * "Share this week's picks" — the model's weekly pick slip as a PNG.
 *
 * Share flow: native share sheet where supported (mobile). canShare() can
 * report true while share() still rejects (headless/desktop Chrome) — only a
 * user cancellation ends there; any other failure falls through to the
 * in-page dialog so the button is never dead.
 */
export default function SharePicks({ label = "Share this week's picks" }: { label?: string }) {
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<SharePreview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const closeDialog = () => {
    if (preview) URL.revokeObjectURL(preview.url);
    setPreview(null);
    setError(null);
  };

  const share = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/pick-slip");
      if (!res.ok) throw new Error("Could not generate image.");
      const blob = await res.blob();
      const file = new File([blob], "honest-line-picks.png", { type: "image/png" });
      // Native share sheet where supported (mobile).
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        try {
          await navigator.share({
            files: [file],
            title: "Honest Line picks",
            text: "This week's Honest Line model picks — full graded record at honest-line.vercel.app",
          });
          return; // shared — done
        } catch (e) {
          if (e instanceof Error && e.name === "AbortError") return; // user cancelled
          // fall through to dialog
        }
      }
      // Fallback: in-page preview dialog. Works with zero native share support.
      setPreview({
        url: URL.createObjectURL(blob),
        filename: "honest-line-picks.png",
        pageUrl: window.location.href,
      });
    } catch (e) {
      // Fetch/render failure: explicit error state, never silent.
      setError(e instanceof Error ? e.message : "Could not generate the image.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
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
      <SharePreviewDialog
        preview={preview}
        error={error}
        onClose={closeDialog}
        dialogLabel="Share this week's picks"
        imageAlt="This week's Honest Line model picks"
      />
    </>
  );
}
