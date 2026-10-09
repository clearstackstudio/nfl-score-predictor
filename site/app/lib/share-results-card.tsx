"use client";

import { useState } from "react";
import SharePreviewDialog, { type SharePreview } from "./share-dialog";

/**
 * Shareable results card — the pick'em viral loop.
 *
 * Renders the player's graded record vs the model's as a branded PNG entirely
 * client-side (canvas). This must be client-side: pick'em entries live only in
 * browser localStorage, so no server endpoint can ever see them.
 *
 * Share flow: native share sheet where supported (mobile). Anywhere else —
 * or if the native share throws — falls back to an in-page preview dialog
 * with Download PNG + copy-link buttons. Every click produces visible
 * feedback (loading → dialog or error); the button is never dead.
 */
export type CardTally = { w: number; l: number; p: number };

type Tallies = { ats: CardTally; su: CardTally; ou: CardTally };

type Props = {
  sport: string; // "NFL" | "CFB" | "NBA"
  period: string; // "Week 5" | "Tonight's slate"
  path: string; // "/pick-em" — page path for the share link
  you: Tallies;
  model: Tallies;
  shape?: "wide" | "square";
};

const BG = "#09090b";
const AMBER = "#fbbf24";
const WHITE = "#fafafa";
const MUTED = "#a1a1aa";
const FAINT = "#71717a";
const HAIRLINE = "#27272a";

function fmtTally(t: CardTally) {
  return `${t.w}-${t.l}${t.p ? `-${t.p}` : ""}`;
}
function played(t: CardTally) {
  return t.w + t.l + t.p > 0;
}

const CATS = [
  { key: "ats", short: "ATS", label: "Against the spread" },
  { key: "su", short: "straight up", label: "Straight up" },
  { key: "ou", short: "on totals", label: "Over / Under" },
] as const;

function headlineFor(you: Tallies): { text: string; sub: string } | null {
  for (const c of CATS) {
    const t = you[c.key];
    if (played(t)) return { text: `I went ${fmtTally(t)} ${c.short}.`, sub: "Beat that." };
  }
  return null;
}

type CardData = {
  sport: string;
  period: string;
  url: string;
  you: Tallies;
  model: Tallies;
  hero: { text: string; sub: string } | null;
};

function drawCard(ctx: CanvasRenderingContext2D, W: number, H: number, d: CardData) {
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, W, H);
  // Top accent bar
  ctx.fillStyle = AMBER;
  ctx.fillRect(0, 0, W, 6);

  const pad = Math.round(W * 0.053);
  const left = pad;
  const right = W - pad;
  try {
    (ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = "7px";
  } catch { /* older canvas: ignore */ }

  // Header
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";
  ctx.fillStyle = AMBER;
  ctx.font = `700 ${Math.round(H * 0.054)}px system-ui, -apple-system, sans-serif`;
  const hy = Math.round(H * 0.115);
  ctx.fillText("HONEST LINE", left, hy);
  ctx.textAlign = "right";
  ctx.fillStyle = MUTED;
  ctx.font = `500 ${Math.round(H * 0.042)}px system-ui, -apple-system, sans-serif`;
  try {
    (ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = "2px";
  } catch { /* ignore */ }
  ctx.fillText(`${d.sport} PICK'EM · ${d.period.toUpperCase()}`, right, hy);
  try {
    (ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = "0px";
  } catch { /* ignore */ }

  // Divider
  const dy = Math.round(H * 0.175);
  ctx.fillStyle = HAIRLINE;
  ctx.fillRect(left, dy, W - pad * 2, 2);

  // Headline
  const big = Math.round(H * 0.108);
  ctx.textAlign = "left";
  ctx.font = `800 ${big}px system-ui, -apple-system, sans-serif`;
  const h1y = Math.round(H * 0.335);
  const h2y = Math.round(H * 0.335 + big * 1.12);
  if (d.hero) {
    ctx.fillStyle = WHITE;
    ctx.fillText(d.hero.text, left, h1y);
    ctx.fillStyle = AMBER;
    ctx.fillText(d.hero.sub, left, h2y);
  } else {
    ctx.fillStyle = WHITE;
    ctx.fillText("Think you can", left, h1y);
    ctx.fillStyle = AMBER;
    ctx.fillText("beat the model?", left, h2y);
  }

  // You vs model table
  const ty = Math.round(H * 0.62);
  const rowH = Math.round(H * 0.075);
  const youX = Math.round(W * 0.62);
  const modX = Math.round(W * 0.85);
  ctx.font = `700 ${Math.round(H * 0.042)}px system-ui, -apple-system, sans-serif`;
  ctx.textAlign = "center";
  ctx.fillStyle = AMBER;
  ctx.fillText("YOU", youX, ty);
  ctx.fillStyle = WHITE;
  ctx.fillText("MODEL", modX, ty);

  ctx.font = `500 ${Math.round(H * 0.04)}px system-ui, -apple-system, sans-serif`;
  CATS.forEach((c, i) => {
    const ry = ty + rowH * (i + 1);
    ctx.textAlign = "left";
    ctx.fillStyle = MUTED;
    ctx.fillText(c.label, left, ry);
    ctx.textAlign = "center";
    ctx.fillStyle = AMBER;
    ctx.font = `700 ${Math.round(H * 0.048)}px ui-monospace, SFMono-Regular, monospace`;
    ctx.fillText(fmtTally(d.you[c.key]), youX, ry);
    ctx.fillStyle = WHITE;
    ctx.fillText(fmtTally(d.model[c.key]), modX, ry);
    ctx.font = `500 ${Math.round(H * 0.04)}px system-ui, -apple-system, sans-serif`;
  });

  // Footer
  ctx.textAlign = "left";
  ctx.font = `400 ${Math.round(H * 0.034)}px system-ui, -apple-system, sans-serif`;
  ctx.fillStyle = FAINT;
  const fy = H - Math.round(H * 0.055);
  const pre = "No edge claimed. Play free: ";
  ctx.fillText(pre, left, fy);
  const preW = ctx.measureText(pre).width;
  ctx.fillStyle = AMBER;
  ctx.fillText(d.url.replace(/^https?:\/\//, ""), left + preW, fy);
}

async function renderBlob(
  d: CardData,
  shape: "wide" | "square"
): Promise<{ blob: Blob; filename: string }> {
  const W = shape === "wide" ? 1200 : 1080;
  const H = shape === "wide" ? 630 : 1080;
  // Render at 2x for crisp text, export at full resolution.
  const canvas = document.createElement("canvas");
  canvas.width = W * 2;
  canvas.height = H * 2;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas unavailable.");
  ctx.scale(2, 2);
  drawCard(ctx, W, H, d);
  const blob = await new Promise<Blob | null>((res) =>
    canvas.toBlob(res, "image/png")
  );
  if (!blob) throw new Error("Could not generate image.");
  const slug = `${d.sport.toLowerCase()}-${d.period.toLowerCase().replace(/[^a-z0-9]+/g, "")}`;
  return { blob, filename: `honest-line-pickem-${slug}${shape === "square" ? "-square" : ""}.png` };
}

export default function ShareResultsCard({
  sport,
  period,
  path,
  you,
  model,
  shape = "wide",
}: Props) {
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
      const url = `${window.location.origin}${path}`;
      const hero = headlineFor(you);
      const { blob, filename } = await renderBlob(
        { sport, period, url, you, model, hero },
        shape
      );
      const file = new File([blob], filename, { type: "image/png" });
      const text = hero
        ? `${hero.text} ${hero.sub} Honest Line ${sport} Pick'em (${period}) — ${url}`
        : `Think you can beat the Honest Line ${sport} model? Play free: ${url}`;
      // Native share sheet where supported (mobile). canShare() can report
      // true while share() still rejects (headless/desktop Chrome) — only a
      // user cancellation ends here; any other failure falls through to the
      // in-page dialog so the button is never dead.
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        try {
          await navigator.share({
            files: [file],
            title: "Honest Line Pick'em",
            text,
          });
          return; // shared — done
        } catch (e) {
          if (e instanceof Error && e.name === "AbortError") return; // user cancelled
          // fall through to dialog
        }
      }
      // Fallback: in-page preview dialog. Works with zero native share support.
      setPreview({ url: URL.createObjectURL(blob), filename, pageUrl: url });
    } catch (e) {
      // Canvas/render failure: explicit error state, never silent.
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
        {busy ? "Preparing…" : shape === "square" ? "Share square card" : "Share your results"}
      </button>

      <SharePreviewDialog
        preview={preview}
        error={error}
        onClose={closeDialog}
        dialogLabel="Share your results"
        imageAlt="Your Honest Line pick'em results card"
        errorTitle="Couldn't make your card"
      />
    </>
  );
}
