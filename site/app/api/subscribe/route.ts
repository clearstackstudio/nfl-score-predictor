import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const { email } = (await req.json().catch(() => ({}))) as { email?: string };
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json({ error: "Please enter a valid email address." }, { status: 400 });
  }

  const apiKey = process.env.RESEND_API_KEY;
  const audienceId = process.env.RESEND_AUDIENCE_ID;
  if (!apiKey || !audienceId) {
    return NextResponse.json(
      { error: "Email signup is not configured yet. Please try again later." },
      { status: 503 }
    );
  }

  try {
    const res = await fetch(`https://api.resend.com/audiences/${audienceId}/contacts`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email }),
    });
    if (!res.ok) {
      const d = await res.json().catch(() => null);
      // Already subscribed is fine — treat as success
      if (d?.name === "validation_error") {
        return NextResponse.json({ ok: true, already: true });
      }
      throw new Error(d?.message || `Resend ${res.status}`);
    }
    return NextResponse.json({ ok: true });
  } catch (e) {
    console.error("subscribe failed:", e);
    return NextResponse.json(
      { error: "Something went wrong. Please try again later." },
      { status: 500 }
    );
  }
}
