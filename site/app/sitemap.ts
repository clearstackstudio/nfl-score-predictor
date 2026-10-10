import type { MetadataRoute } from "next";

// Public routes only. The four /methodology routes are intentionally excluded:
// they return 401 behind HTTP Basic Auth and listing them would create crawl errors.
const routes = [
  "",
  "/accuracy",
  "/calibration",
  "/disclaimer",
  "/live",
  "/pick-em",
  "/recaps",
  "/tracker",
  "/track-record",
  "/cfb",
  "/cfb/live",
  "/cfb/pick-em",
  "/cfb/track-record",
  "/nba",
  "/nba/live",
  "/nba/pick-em",
  "/nba/track-record",
  "/ncaab",
  "/ncaab/live",
  "/ncaab/pick-em",
  "/ncaab/track-record",
  "/mlb",
  "/mlb/pick-em",
  "/mlb/track-record",
];

export default function sitemap(): MetadataRoute.Sitemap {
  return routes.map((route) => ({
    url: `https://honest-line.vercel.app${route}`,
    lastModified: new Date(),
    changeFrequency: route === "" ? "daily" : "weekly",
    priority: route === "" ? 1 : 0.7,
  }));
}
