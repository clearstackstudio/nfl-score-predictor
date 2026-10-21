// ads.txt — declares authorized digital sellers for honestlinesports.com.
// When NEXT_PUBLIC_ADSENSE_ID is set (ca-pub-… or pub-…), serves the
// standard Google line. Until then, a comment-only file: valid ads.txt,
// zero sellers authorized.
export const dynamic = "force-dynamic";

export function GET() {
  const id = process.env.NEXT_PUBLIC_ADSENSE_ID ?? "";
  const pub = id.replace(/^ca-/, "");
  const body = pub
    ? `google.com, ${pub}, DIRECT, f08c47fec0942fa0\n`
    : "# ads.txt — no advertising partners configured yet.\n";
  return new Response(body, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
