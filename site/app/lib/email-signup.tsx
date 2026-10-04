"use client";

import { useState } from "react";

export default function EmailSignup() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [msg, setMsg] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setStatus("loading");
    setMsg("");
    try {
      const res = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const d = await res.json().catch(() => null);
      if (!res.ok) throw new Error(d?.error || "Signup failed.");
      setStatus("done");
    } catch (err) {
      setStatus("error");
      setMsg(err instanceof Error ? err.message : "Signup failed.");
    }
  };

  if (status === "done") {
    return (
      <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/5 p-6 text-center light:border-emerald-600/20 light:bg-emerald-50">
        <p className="font-semibold text-emerald-400 light:text-emerald-700">You're on the list.</p>
        <p className="mt-1 text-sm text-zinc-400 light:text-zinc-600">
          The picks land in your inbox every week. Unsubscribe anytime.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 light:border-zinc-200 light:bg-white">
      <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">
        Get the picks <span className="text-amber-400 light:text-amber-600">weekly</span>
      </h2>
      <p className="mt-2 text-sm text-zinc-400 light:text-zinc-600">
        Every week's model picks, plus the graded results — wins and losses, no cherry-picking.
        Free, unsubscribe anytime.
      </p>
      <form onSubmit={submit} className="mt-4 flex flex-col gap-3 sm:flex-row">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="flex-1 rounded-xl border border-zinc-700 bg-zinc-950 px-4 py-3 text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-amber-400 light:border-zinc-300 light:bg-zinc-50 light:text-zinc-900"
        />
        <button
          type="submit"
          disabled={status === "loading"}
          className="rounded-xl bg-amber-400 px-6 py-3 font-bold text-zinc-950 transition hover:bg-amber-300 disabled:opacity-50"
        >
          {status === "loading" ? "Signing up…" : "Sign up"}
        </button>
      </form>
      {status === "error" && <p className="mt-2 text-sm text-red-400">{msg}</p>}
    </div>
  );
}
