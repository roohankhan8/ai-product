"use client";

import { FormEvent, useState } from "react";
import { api } from "../lib/api";

export function SignIn({ onSuccess }: { onSuccess: (token: string) => void }) {
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await api("/auth/dev-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      onSuccess(data.access_token);
    } catch {
      setError("We couldn’t sign you in. Check the email and try again.");
    } finally {
      setLoading(false);
    }
  };
  return (
    <main className="relative grid h-dvh min-h-0 place-items-center overflow-hidden bg-[#eaf3ef] p-4 sm:p-6">
      <div className="absolute left-0 top-0 h-72 w-72 rounded-full bg-[#cce7df] blur-3xl" />
      <div className="absolute bottom-0 right-0 h-80 w-80 rounded-full bg-[#f6d8cb] blur-3xl" />
      <div className="relative grid h-full max-h-[720px] w-full max-w-5xl min-h-0 overflow-hidden rounded-3xl border border-white/80 bg-white shadow-2xl shadow-[#24564d]/15 md:grid-cols-[.95fr_1.05fr]">
        <aside className="relative hidden min-h-0 overflow-hidden bg-[#087f73] p-10 text-white md:flex md:flex-col md:justify-between lg:p-14">
          <div>
            <div className="text-xl font-extrabold tracking-tight">
              <span className="text-[#f4aa8e]">✦</span> Northstar
            </div>
            <span className="mt-8 inline-flex rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[.14em] text-[#b9e0d8]">
              AI operations platform
            </span>
          </div>
          <div>
            <h1 className="max-w-md text-4xl font-bold leading-[.98] tracking-[-.06em] lg:text-6xl">
              Bring your company knowledge into focus.
            </h1>
            <p className="mt-6 max-w-sm leading-6 text-[#c6e8df]">
              Search trusted internal documents and ask grounded questions with
              sources attached.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-[#b9e0d8]">
            <span className="h-2 w-2 rounded-full bg-[#f4aa8e]" />
            Grounded answers. Clear sources.
          </div>
        </aside>
        <section className="flex min-h-0 flex-col justify-center overflow-hidden px-6 py-8 sm:px-12 lg:px-16">
          <div className="mb-8 md:hidden">
            <div className="text-xl font-extrabold tracking-tight text-[#17323a]">
              <span className="text-[#e78361]">✦</span> Northstar
            </div>
            <p className="mt-2 text-sm text-[#6b7d80]">Your company knowledge, in focus.</p>
          </div>
          <div className="max-w-md">
            <p className="text-[11px] font-extrabold uppercase tracking-[.15em] text-[#087f73]">
              Welcome back
            </p>
            <h2 className="mt-3 text-3xl font-bold tracking-[-.05em] text-[#17323a] sm:text-4xl">
              Sign in to your workspace
            </h2>
            <p className="mt-3 text-sm leading-6 text-[#6b7d80]">
              Continue to your documents, conversations, and grounded answers.
            </p>
            <form onSubmit={submit} className="mt-8 grid gap-2.5">
              <label className="text-sm font-bold text-[#17323a]" htmlFor="email">
                Work email
              </label>
              <input
                className="h-12 rounded-xl border border-[#dce8e5] bg-[#fbfdfc] px-4 outline-none transition focus:border-[#087f73] focus:ring-4 focus:ring-[#087f73]/10"
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
              <label className="mt-2 text-sm font-bold text-[#17323a]" htmlFor="password">
                Password
              </label>
              <input
                className="h-12 rounded-xl border border-[#dce8e5] bg-[#fbfdfc] px-4 outline-none transition focus:border-[#087f73] focus:ring-4 focus:ring-[#087f73]/10"
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
              <button
                className="mt-3 h-12 rounded-xl bg-[#087f73] px-5 font-bold text-white transition hover:bg-[#056259] disabled:cursor-not-allowed disabled:opacity-50"
                disabled={loading}
              >
                {loading ? "Signing in…" : "Continue to workspace  →"}
              </button>
              {error && (
                <p className="rounded-lg bg-[#fff1ed] px-3 py-2 text-sm text-[#b84d3c]" role="alert">
                  {error}
                </p>
              )}
            </form>
          </div>
        </section>
      </div>
    </main>
  );
}
