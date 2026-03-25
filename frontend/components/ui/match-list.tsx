"use client";

import { LockIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { getToken } from "@/lib/auth";
import { ApiMatch, formatKickoff, riskColors, riskLabel } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const FREE_SLOTS = 3;

async function fetchPlan(): Promise<string> {
  const token = getToken();
  if (!token) return "STARTER";
  try {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), 8000);
    const res = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    });
    const json = await res.json();
    return json?.data?.subscription_plan ?? "STARTER";
  } catch {
    return "STARTER";
  }
}

export default function MatchList({ matches }: { matches: ApiMatch[] }) {
  const [plan, setPlan] = useState<string | null>(null);

  useEffect(() => {
    fetchPlan().then(setPlan);
  }, []);

  const isPro = plan === "PRO" || plan === "ELITE";
  const unlockedMatches = isPro ? matches : matches.slice(0, FREE_SLOTS);
  const lockedMatches = isPro ? [] : matches.slice(FREE_SLOTS);

  if (plan === null) {
    return <div className="text-sm text-[#7A8FA8] animate-pulse">Chargement…</div>;
  }

  return (
    <div className="flex gap-6 flex-col lg:flex-row">
      <div className="flex-1 flex flex-col gap-3">
        <div className="text-sm font-semibold text-[#7A8FA8] uppercase tracking-wide">
          Analyses disponibles
        </div>

        {unlockedMatches.map((match) => {
          const colors = riskColors(match.risk_level);
          return (
            <div
              key={match.id}
              className="rounded-xl border border-[#1E2D42] bg-[#0E1828] p-4 flex items-center gap-4"
              style={{ borderLeft: `3px solid ${colors.border}` }}
            >
              <div className="flex-1 min-w-0">
                <div className="font-bold text-[#DDD5C4] truncate" style={{ fontFamily: "var(--font-heading, sans-serif)" }}>
                  {match.home_team} vs {match.away_team}
                </div>
                <div className="text-xs text-[#7A8FA8]">
                  {match.league} · {formatKickoff(match.kickoff_at)}
                </div>
                {match.recommended_bet && (
                  <div className="text-xs text-[#C8F000] mt-0.5">{match.recommended_bet}</div>
                )}
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="font-[family-name:var(--font-mono)] font-semibold text-lg" style={{ color: "#C8F000" }}>
                  +{match.value_percent?.toFixed(1)}%
                </span>
                <div className="flex flex-col items-end gap-1">
                  <span className="text-xs px-2 py-0.5 rounded font-medium" style={{ background: colors.bg, color: colors.text }}>
                    {riskLabel(match.risk_level)}
                  </span>
                  <span className="text-xs text-[#7A8FA8] font-[family-name:var(--font-mono)]">
                    {match.confidence_score?.toFixed(0)}% conf.
                  </span>
                </div>
              </div>
            </div>
          );
        })}

        {lockedMatches.map((match) => (
          <div
            key={match.id}
            className="relative rounded-xl border border-[#1E2D42] bg-[#0E1828] p-4 flex items-center gap-4 overflow-hidden"
          >
            <div
              className="absolute inset-0 flex flex-col items-center justify-center gap-2 z-10 rounded-xl"
              style={{ background: "rgba(6,9,15,0.82)", backdropFilter: "blur(6px)" }}
            >
              <LockIcon className="size-5" style={{ color: "#C8F000" }} />
              <span className="text-xs text-[#7A8FA8]">
                Réservé aux membres{" "}
                <Link href="/#pricing" className="font-semibold underline" style={{ color: "#C8F000" }}>Pro</Link>
              </span>
            </div>
            <div className="flex-1 min-w-0 blur-sm select-none">
              <div className="font-bold text-[#DDD5C4] truncate">{match.home_team} vs {match.away_team}</div>
              <div className="text-xs text-[#7A8FA8]">{match.league}</div>
            </div>
            <div className="flex items-center gap-3 shrink-0 blur-sm select-none">
              <span className="font-[family-name:var(--font-mono)] font-semibold text-lg" style={{ color: "#C8F000" }}>
                +{match.value_percent?.toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      <aside className="w-full lg:w-[260px] shrink-0 flex flex-col gap-4">
        <div className="rounded-xl border border-[#1E2D42] bg-[#0E1828] p-4 flex flex-col gap-3">
          <div className="text-sm font-semibold text-[#DDD5C4]">À propos de l&apos;algorithme</div>
          <p className="text-xs text-[#7A8FA8] leading-relaxed">
            Combinaison Elo + Poisson + XGBoost entraîné sur 4 000+ matchs. Les écarts détectés reflètent des
            divergences entre probabilités réelles estimées et cotes implicites bookmakers.
          </p>
          <div className="text-xs text-[#7A8FA8] font-[family-name:var(--font-mono)]">
            Précision globale : <span style={{ color: "#C8F000" }}>57.6%</span>
          </div>
        </div>

        {!isPro && (
          <div
            className="rounded-xl border p-4 flex flex-col gap-3"
            style={{ borderColor: "rgba(200,240,0,0.25)", background: "rgba(200,240,0,0.04)" }}
          >
            <div className="text-sm font-semibold" style={{ color: "#C8F000" }}>Passe en Pro</div>
            <p className="text-xs text-[#7A8FA8] leading-relaxed">
              Débloque les analyses restantes, les explications complètes et l&apos;historique.
            </p>
            <Link
              href="/#pricing"
              className="inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-semibold transition-colors"
              style={{ background: "#C8F000", color: "#06090F" }}
            >
              Voir les tarifs
            </Link>
          </div>
        )}

        <div className="text-xs text-[#7A8FA8] leading-relaxed px-1">
          RushPlay est un outil d&apos;analyse statistique. Aucun gain garanti. Jouez responsable — aide : 09 74 75 13 13
        </div>
      </aside>
    </div>
  );
}
