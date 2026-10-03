"use client";

import { FormEvent, useState } from "react";
import { api } from "../lib/api";

export function SignIn({ onSuccess }: { onSuccess: (token: string) => void }) {
  const [email, setEmail] = useState("user@example.com");
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
        body: JSON.stringify({ email }),
      });
      onSuccess(data.access_token);
    } catch {
      setError("We couldn’t sign you in. Check the email and try again.");
    } finally {
      setLoading(false);
    }
  };
  return (
    <main className="grid min-h-screen grid-cols-1 md:grid-cols-[minmax(0,1fr)_42%]">
      <section className="mx-auto flex w-full max-w-xl flex-col justify-center px-7 py-12 md:px-12">
        <div className="text-xl font-extrabold tracking-tight">
          <span className="text-[#e78361]">✦</span> Northstar
        </div>
        <p className="mt-16 text-[11px] font-extrabold uppercase tracking-[.13em] text-[#087f73]">
          AI operations platform
        </p>
        <h1 className="mt-4 max-w-xl text-5xl font-bold leading-[.98] tracking-[-.065em] md:text-7xl">
          Bring your company knowledge into focus.
        </h1>
        <p className="mt-6 max-w-lg leading-7 text-[#6b7d80]">
          Search trusted internal documents and ask grounded questions with
          sources attached.
        </p>
        <form onSubmit={submit} className="mt-9 grid max-w-md gap-2">
          <label className="text-sm font-bold" htmlFor="email">
            Work email
          </label>
          <input
            className="h-12 rounded-lg border border-[#dce8e5] px-4 outline-none focus:border-[#087f73] focus:ring-4 focus:ring-[#087f73]/10"
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <button
            className="mt-2 h-12 rounded-lg bg-[#087f73] px-5 font-bold text-white transition hover:bg-[#056259] disabled:cursor-not-allowed disabled:opacity-50"
            disabled={loading}
          >
            {loading ? "Signing in…" : "Continue →"}
          </button>
          {error && (
            <p className="text-sm text-[#b84d3c]" role="alert">
              {error}
            </p>
          )}
        </form>
      </section>
      <aside className="hidden flex-col justify-end bg-[#087f73] p-16 text-[#effaf6] md:flex">
        <span className="text-[11px] uppercase tracking-[.15em] text-[#9bd5c8]">
          A calmer way to work
        </span>
        <div className="mt-5 max-w-xl text-6xl font-medium leading-none tracking-[-.06em]">
          “The answer is only as useful as the source behind it.”
        </div>
        <div className="my-9 h-px w-60 bg-white/25" />
        <p className="max-w-xs leading-6 text-[#b9e0d8]">
          Keep decisions close to the context that makes them trustworthy.
        </p>
      </aside>
    </main>
  );
}
