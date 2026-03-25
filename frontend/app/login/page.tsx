"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import RushPlayLogo from "../../components/logos/rushplay";
import { login } from "../../lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#06090F] px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center gap-2.5 justify-center mb-8">
          <RushPlayLogo />
          <span
            className="text-xl font-bold text-[#DDD5C4]"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            RushPlay
          </span>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-[#1E2D42] bg-[#0E1828] p-8">
          <h1 className="text-xl font-bold text-[#DDD5C4] mb-1" style={{ fontFamily: "var(--font-heading, sans-serif)" }}>
            Connexion
          </h1>
          <p className="text-sm text-[#7A8FA8] mb-6">
            Accède à tes signaux du jour.
          </p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-[#7A8FA8]">Email</label>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="toi@exemple.com"
                className="w-full rounded-lg border border-[#1E2D42] bg-[#06090F] px-3 py-2.5 text-sm text-[#DDD5C4] placeholder-[#3A4F65] outline-none focus:border-[#C8F000] transition-colors"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-[#7A8FA8]">Mot de passe</label>
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-lg border border-[#1E2D42] bg-[#06090F] px-3 py-2.5 text-sm text-[#DDD5C4] placeholder-[#3A4F65] outline-none focus:border-[#C8F000] transition-colors"
              />
            </div>

            {error && (
              <div className="rounded-lg border border-[#f87171] bg-[rgba(248,113,113,0.08)] px-3 py-2 text-xs text-[#f87171]">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="mt-1 w-full rounded-lg py-2.5 text-sm font-semibold transition-opacity disabled:opacity-60"
              style={{ background: "#C8F000", color: "#06090F" }}
            >
              {loading ? "Connexion…" : "Se connecter"}
            </button>
          </form>
        </div>

        <p className="mt-4 text-center text-sm text-[#7A8FA8]">
          Pas encore de compte ?{" "}
          <Link href="/register" className="text-[#C8F000] hover:underline font-medium">
            S&apos;inscrire
          </Link>
        </p>
      </div>
    </div>
  );
}
