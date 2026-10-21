"use client";

import { useState, type ReactNode } from "react";

// Shared collapse/expand pattern for grouped cards, copied from the live
// page (app/live/page.tsx) so every collapsible card on the site uses the
// same pill, chevron, and fold animation. The live page keeps its own
// copies; these are the same classes and behavior.

/** Chevron for a collapsible card header; points right when folded. */
function Chevron({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 20 20" className={`h-4 w-4 shrink-0 text-zinc-400 transition-transform duration-300 light:text-zinc-500 ${open ? "" : "-rotate-90"}`} fill="none" aria-hidden="true">
      <path d="M5 7.5 10 12.5 15 7.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Labeled Collapse/Expand pill shown in each card's toggle control. */
export function CollapsePill({ open }: { open: boolean }) {
  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-white/15 bg-white/5 px-2.5 py-1 text-[11px] font-semibold normal-case tracking-normal text-zinc-300 light:border-zinc-300 light:bg-zinc-50 light:text-zinc-600">
      {open ? "Collapse" : "Expand"}
      <Chevron open={open} />
    </span>
  );
}

/** Smoothly folds its children away (grid-rows animation) when closed. */
export function CollapseRegion({ open, children }: { open: boolean; children: ReactNode }) {
  return (
    <div className={`grid transition-all duration-300 ease-out ${open ? "[grid-template-rows:1fr] opacity-100" : "[grid-template-rows:0fr] opacity-0"}`}>
      <div className="min-h-0 overflow-hidden">{children}</div>
    </div>
  );
}

/** A group with a header row (header content left, Collapse/Expand pill
 * right) whose body folds away when collapsed. The header stays fully
 * visible in both states; each group toggles independently. */
export default function CollapsibleGroup({
  header,
  defaultOpen = false,
  className,
  children,
}: {
  header: ReactNode;
  defaultOpen?: boolean;
  className?: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={className}>
      <div className="flex items-center justify-between gap-3">
        {header}
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-label={open ? "Collapse section" : "Expand section"}
          className="shrink-0"
        >
          <CollapsePill open={open} />
        </button>
      </div>
      <CollapseRegion open={open}>{children}</CollapseRegion>
    </div>
  );
}
