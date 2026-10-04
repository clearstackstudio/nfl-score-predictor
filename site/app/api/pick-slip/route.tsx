import { ImageResponse } from "next/og";
import picksData from "../../../data/picks.json";

export const runtime = "edge";

type Pick = {
  away_abbr: string; home_abbr: string;
  pick_spread_label: string | null;
  pick_total_label: string | null;
  cover_prob: number | null; ou_prob: number | null;
};

const picks = (picksData.picks as Pick[]).filter(
  (p) => p.pick_spread_label || p.pick_total_label
);

function pct(x: number | null): string {
  if (x == null) return "";
  return ` · ${Math.round(x * 100)}%`;
}

export async function GET() {
  const week = (picksData as any).week;
  const season = (picksData as any).season;
  return new ImageResponse(
    (
      <div
        style={{
          width: "1080px", height: "1560px",
          backgroundColor: "#09090b",
          color: "#fafafa",
          fontFamily: "system-ui, -apple-system, sans-serif",
          display: "flex", flexDirection: "column",
          padding: "48px 56px",
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
          <div style={{ fontSize: 40, fontWeight: 800, letterSpacing: 4, color: "#fbbf24" }}>
            HONEST LINE
          </div>
          <div style={{ fontSize: 26, color: "#a1a1aa" }}>
            {`NFL · Week ${week} ${season}`}
          </div>
        </div>
        <div style={{ fontSize: 24, color: "#d4d4d8", marginTop: 6 }}>
          {`Our model's picks — receipts on the site, win or lose.`}
        </div>
        <div style={{ height: 2, backgroundColor: "#27272a", margin: "24px 0" }} />

        <div style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>
          {picks.map((p) => (
            <div key={`${p.away_abbr}-${p.home_abbr}`} style={{ display: "flex", alignItems: "center" }}>
              <div style={{ width: 210, fontSize: 27, fontWeight: 700, display: "flex", gap: 8 }}>
                <span>{p.away_abbr}</span>
                <span style={{ color: "#71717a" }}>@</span>
                <span>{p.home_abbr}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                {p.pick_spread_label && (
                  <div style={{ fontSize: 23, color: "#e4e4e7", display: "flex", gap: 8 }}>
                    <span>{p.pick_spread_label}</span>
                    <span style={{ color: "#a1a1aa" }}>{`${pct(p.cover_prob)} to cover`}</span>
                  </div>
                )}
                {p.pick_total_label && (
                  <div style={{ fontSize: 23, color: "#e4e4e7", display: "flex", gap: 8 }}>
                    <span>{p.pick_total_label}</span>
                    <span style={{ color: "#a1a1aa" }}>{pct(p.ou_prob)}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div style={{ height: 2, backgroundColor: "#27272a", margin: "24px 0" }} />
        <div style={{ fontSize: 22, color: "#a1a1aa" }}>
          {`No edge claimed. Full graded record:`}
        </div>
        <div style={{ fontSize: 28, fontWeight: 700, color: "#fbbf24", marginTop: 4 }}>
          {`honest-line.vercel.app`}
        </div>
      </div>
    ),
    { width: 1080, height: 1560 }
  );
}
