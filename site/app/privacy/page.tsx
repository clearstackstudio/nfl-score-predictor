import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    "How Honest Line handles your information: no accounts, picks stored in your browser, an optional public leaderboard, and how Google advertising cookies work.",
  alternates: { canonical: "/privacy" },
};

const sections = [
  {
    n: "01",
    title: "What this site is",
    body: [
      "Honest Line (honestlinesports.com) is a sports prediction and information site published by ClearStack Studio. There are no user accounts and no registration — you never need an email address or password to read anything here.",
    ],
  },
  {
    n: "02",
    title: "What our servers see",
    body: [
      "Like almost every website, our hosting provider keeps standard server logs: your IP address, browser type, the pages you visit, and when. We use those logs to run and secure the site, not to identify or profile individual readers. IP addresses are also used briefly to rate-limit leaderboard submissions and prevent abuse.",
    ],
  },
  {
    n: "03",
    title: "Stored in your browser",
    body: [
      "Our pick'em games, bet tracker, and leaderboard display name are saved in your browser's local storage so the site can remember them between visits. That information stays on your device — it is never sent to us while you browse. You can delete it at any time by clearing this site's cookies and site data in your browser settings.",
    ],
  },
  {
    n: "04",
    title: "The pick'em leaderboard",
    body: [
      "Joining the leaderboard is optional. If you choose to submit a card, the display name you pick and your picks for that week or day are stored on our servers so your record can be graded and shown. Your display name and record are public on the leaderboard — please don't use a name that identifies you personally if you don't want it visible.",
    ],
  },
  {
    n: "05",
    title: "Cookies and advertising",
    body: [
      "We use cookies and local storage for site function, such as remembering the picks described above. Advertising on this site is served by Google AdSense.",
      "Third-party vendors, including Google, use cookies to serve ads based on a user's prior visits to this website and other websites. Google's use of advertising cookies enables it and its partners to serve ads to our users based on their visit to this site and/or other sites on the Internet. Google also uses the DoubleClick (DART) cookie for ad serving; visitors may opt out of the DART cookie by visiting Google's Ads Settings.",
      "You may opt out of personalized advertising by visiting Google's Ads Settings (https://www.google.com/settings/ads). You can also opt out of some third-party vendors' use of cookies for personalized advertising at https://www.aboutads.info.",
    ],
  },
  {
    n: "06",
    title: "Third parties and your information",
    body: [
      "Other than Google AdSense for advertising and our hosting provider for delivering the site, we do not share visitor information with third parties. The sources we use for scores, lines, and statistics receive no personal information about our visitors.",
      "We do not sell personal information.",
    ],
  },
  {
    n: "07",
    title: "Children and adults",
    body: [
      "This site is not directed at children under 13. Because the content discusses sports betting, it is intended for adults 21 and over, consistent with our disclaimers page.",
    ],
  },
  {
    n: "08",
    title: "Changes and contact",
    body: [
      "If we change this policy, the updated version will be posted on this page with a new effective date. Questions about this policy can be sent to helloclearstackstudio@gmail.com.",
    ],
  },
];

export default function Privacy() {
  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        The fine print
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Privacy <span className="text-amber-400 light:text-amber-600">Policy</span>
      </h1>
      <p className="mt-4 text-[15px] text-zinc-400 light:text-zinc-600">
        The short version: no accounts, no emails collected, and most of what
        you do here never leaves your browser. Advertising keeps the site
        free — how that works is spelled out below.
      </p>

      {sections.map((s) => (
        <section
          key={s.n}
          className="mt-8 rounded-2xl border border-white/10 bg-zinc-900/40 p-6 sm:p-8 light:border-zinc-200 light:bg-white"
        >
          <div className="flex items-baseline gap-4">
            <span className="tnum font-display text-lg font-semibold text-amber-400/80 light:text-amber-700">
              {s.n}
            </span>
            <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">
              {s.title}
            </h2>
          </div>
          <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
            {s.body.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </section>
      ))}

      <p className="mt-8 text-xs leading-relaxed text-zinc-500 light:text-zinc-500">
        Effective October 22, 2026. This page is general information, not
        legal advice. If you need legal guidance about privacy law, consult a
        qualified attorney.
      </p>
    </div>
  );
}
