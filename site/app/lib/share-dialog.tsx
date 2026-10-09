"use client";

import { useEffect, useState } from "react";

/**
 * Shared in-page fallback for share buttons.
 *
 * Used when the native share sheet is unavailable or fails: shows a preview
 * dialog with the generated image plus Download PNG and Copy link buttons.
 * The parent owns the preview object-URL lifecycle (revoke on close) and
 * passes its error state through. Every click on the share button produces
 * visible feedback (loading → dialog or error); the button is never dead.
 */
export type SharePreview = { url: string; filename: string; pageUrl: string };

type Props = {
  preview: SharePreview | null;
  error: string | null;
  onClose: () => void;
  dialogLabel: string;
  imageAlt: string;
  errorTitle?: string;
};

export default function SharePreviewDialog({
  preview,
  error,
  onClose,
  dialogLabel,
  imageAlt,
  errorTitle = "Couldn't make the image",
}: Props) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!preview && !error) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const copyLink = async () => {
    if (!preview) return;
    try {
      await navigator.clipboard.writeText(preview.pageUrl);
    } catch {
      // Clipboard API unavailable (e.g. non-secure context): legacy fallback.
      const ta = document.createElement("textarea");
      ta.value = preview.pageUrl;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy");
      } catch {
        /* give up silently — the link is visible in the card */
      }
      ta.remove();
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  if (!preview && !error) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={dialogLabel}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950 light:border-zinc-200 light:bg-white"
        onClick={(e) => e.stopPropagation()}
      >
        {error ? (
          <div className="p-6">
            <h3 className="text-base font-semibold text-zinc-100 light:text-zinc-900">
              {errorTitle}
            </h3>
            <p className="mt-2 text-sm text-zinc-400 light:text-zinc-600">{error}</p>
            <button
              onClick={onClose}
              className="mt-4 rounded-full border border-zinc-700 px-4 py-2 text-sm font-semibold text-zinc-200 transition hover:bg-zinc-800 light:border-zinc-300 light:text-zinc-700 light:hover:bg-zinc-100"
            >
              Close
            </button>
          </div>
        ) : (
          preview && (
            <>
              <img
                src={preview.url}
                alt={imageAlt}
                className="block w-full"
              />
              <div className="flex flex-wrap items-center gap-2 p-4">
                <a
                  href={preview.url}
                  download={preview.filename}
                  className="rounded-full bg-amber-400 px-4 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-amber-300 light:bg-amber-600 light:text-white light:hover:bg-amber-700"
                >
                  Download PNG
                </a>
                <button
                  onClick={copyLink}
                  className="rounded-full border border-amber-400/40 px-4 py-2 text-sm font-semibold text-amber-400 transition hover:bg-amber-400/10 light:border-amber-600/40 light:text-amber-700 light:hover:bg-amber-600/10"
                >
                  {copied ? "Copied!" : "Copy link"}
                </button>
                <button
                  onClick={onClose}
                  className="rounded-full px-4 py-2 text-sm font-semibold text-zinc-400 transition hover:text-zinc-200 light:text-zinc-500 light:hover:text-zinc-800"
                >
                  Close
                </button>
              </div>
            </>
          )
        )}
      </div>
    </div>
  );
}
