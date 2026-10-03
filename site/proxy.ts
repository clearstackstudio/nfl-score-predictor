import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Admin-only pages: HTTP Basic Auth via env vars.
 *  Set ADMIN_USER + ADMIN_PASS in Vercel (all environments). */
const PROTECTED = ["/methodology", "/cfb/methodology", "/nba/methodology"];

export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const isProtected = PROTECTED.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );
  if (!isProtected) return NextResponse.next();

  const user = process.env.ADMIN_USER;
  const pass = process.env.ADMIN_PASS;
  // Fail closed: no credentials configured -> deny everyone.
  if (!user || !pass) return new NextResponse("Not found", { status: 404 });

  const auth = req.headers.get("authorization") || "";
  const [scheme, encoded] = auth.split(" ");
  let ok = false;
  if (scheme === "Basic" && encoded) {
    try {
      const [u, p] = Buffer.from(encoded, "base64").toString().split(":");
      ok = u === user && p === pass;
    } catch {
      ok = false;
    }
  }
  if (!ok) {
    return new NextResponse("Admin only", {
      status: 401,
      headers: { "WWW-Authenticate": 'Basic realm="HonestLine admin"' },
    });
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/methodology/:path*", "/cfb/methodology/:path*", "/nba/methodology/:path*"],
};
