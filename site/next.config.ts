import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async headers() {
    // AdSense hosts (added 2026-10-21, ahead of the account existing — the
    // slots only load the script when NEXT_PUBLIC_ADSENSE_ID is configured,
    // so these allowances are inert until then). Google's documented ad
    // hosts: pagead2/tpc googlesyndication, partner.googleadservices,
    // googletagservices, adservice.google.com, and the doubleclick frame
    // host. img-src already allows https: site-wide, so no change there.
    // frame-ancestors stays 'none' — our pages still can't be framed.
    const csp = "default-src 'self'; script-src 'self' 'unsafe-inline' https://storage.ko-fi.com https://pagead2.googlesyndication.com https://tpc.googlesyndication.com https://partner.googleadservices.com https://www.googletagservices.com https://adservice.google.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; font-src 'self' data: https:; connect-src 'self' https://site.api.espn.com https://ko-fi.com https://storage.ko-fi.com https://pagead2.googlesyndication.com https://tpc.googlesyndication.com https://partner.googleadservices.com https://adservice.google.com; worker-src 'self' blob:; frame-src https://googleads.g.doubleclick.net https://tpc.googlesyndication.com https://pagead2.googlesyndication.com https://partner.googleadservices.com https://www.googletagservices.com https://adservice.google.com; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'";
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Content-Security-Policy", value: csp },
        ],
      },
    ];
  },
};

export default nextConfig;
