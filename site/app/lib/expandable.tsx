"use client";
import { useEffect, useRef, useState } from "react";

// Card content taller than ~5 lines of text collapses to 5 lines behind
// a Show more button (Bryant's request, 2026-10-20). Shorter content
// renders untouched with no button. Line height ~24px matches the
// cards' dominant text sizes.
const LINE_PX = 24;
const MAX_LINES = 5;
const MAX_HEIGHT = LINE_PX * MAX_LINES;

export default function Expandable({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [overflows, setOverflows] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const check = () => setOverflows(el.scrollHeight > MAX_HEIGHT + 4);
    check();
    const ro = new ResizeObserver(check);
    ro.observe(el);
    return () => ro.disconnect();
  }, [children]);

  const clamped = overflows && !open;
  return (
    <div>
      <div
        ref={ref}
        className="relative overflow-hidden"
        style={clamped ? { maxHeight: MAX_HEIGHT } : undefined}
      >
        {children}
        {clamped && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-zinc-900 to-transparent light:from-zinc-50" />
        )}
      </div>
      {overflows && (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="mt-3 w-full rounded-lg border border-white/10 bg-white/5 py-2 text-[13px] font-semibold text-zinc-300 transition-colors hover:bg-white/10 light:border-zinc-200 light:bg-zinc-100 light:text-zinc-700 light:hover:bg-zinc-200"
        >
          {open ? "Show less ▴" : "Show more ▾"}
        </button>
      )}
    </div>
  );
}
