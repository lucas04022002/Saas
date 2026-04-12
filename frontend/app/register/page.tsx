"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import RushPlayLogo from "../../components/logos/rushplay";
import { signup } from "../../lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caractères");
      return;
    }
    setLoading(true);
    try {
      await signup(firstName, lastName, email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de l'inscription");
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
            Créer un compte
          </h1>
          <p className="text-sm text-[#7A8FA8] mb-6">
            30 jours d&apos;essai gratuit, sans carte bancaire.
          </p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex gap-3">
              <div className="flex flex-col gap-1.5 flex-1">
                <label className="text-xs font-medium text-[#7A8FA8]">Prénom</label>
                <input
                  type="text"
                  required
                  autoComplete="given-name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="Prénom"
                  className="w-full rounded-lg border border-[#1E2D42] bg-[#06090F] px-3 py-2.5 text-sm text-[#DDD5C4] placeholder-[#3A4F65] outline-none focus:border-[#C8F000] transition-colors"
                />
              </div>
              <div className="flex flex-col gap-1.5 flex-1">
                <label className="text-xs font-medium text-[#7A8FA8]">Nom</label>
                <input
                  type="text"
                  autoComplete="family-name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Nom"
                  className="w-full rounded-lg border border-[#1E2D42] bg-[#06090F] px-3 py-2.5 text-sm text-[#DDD5C4] placeholder-[#3A4F65] outline-none focus:border-[#C8F000] transition-colors"
                />
              </div>
            </div>

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
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="8 caractères minimum"
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
              {loading ? "Création…" : "Créer mon compte"}
            </button>
          </form>
        </div>

        <p className="mt-4 text-center text-sm text-[#7A8FA8]">
          Déjà un compte ?{" "}
          <Link href="/login" className="text-[#C8F000] hover:underline font-medium">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}
