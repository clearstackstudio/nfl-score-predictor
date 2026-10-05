// Tip-jar link. Empty string = button stays hidden site-wide.
// Bryant: paste your Ko-fi page URL here (e.g. "https://ko-fi.com/yourname")
// once the account is set up, and the button appears automatically.
export const KO_FI_URL = "";

export function SupportButton() {
  if (!KO_FI_URL) return null;
  return (
    <div className="mt-4">
      <a
        href={KO_FI_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-400/10 px-4 py-2 text-sm font-semibold text-amber-300 transition hover:border-amber-400/60 hover:bg-amber-400/20 light:border-amber-600/30 light:bg-amber-600/10 light:text-amber-700 light:hover:border-amber-600/50"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M17 8h1a4 4 0 1 1 0 8h-1" />
          <path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" />
          <line x1="6" y1="2" x2="6" y2="4" />
          <line x1="10" y1="2" x2="10" y2="4" />
          <line x1="14" y1="2" x2="14" y2="4" />
        </svg>
        Support Honest Line
      </a>
      <p className="mt-2 max-w-xs text-xs leading-relaxed text-zinc-500">
        Honest Line is free and reader-supported. Donations go toward hosting
        and data costs — never toward picks.
      </p>
    </div>
  );
}
