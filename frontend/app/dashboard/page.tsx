export const dynamic = "force-dynamic";

import { LockIcon, TrendingUpIcon, ZapIcon } from "lucide-react";
import Link from "next/link";

import RushPlayLogo from "../../components/logos/rushplay";
import UserPlan from "../../components/ui/user-plan";
import { ApiMatch, fetchMatches, formatKickoff, riskColors, riskLabel } from "../../lib/api";

const FREE_SLOTS = 3;

export default async function DashboardPage() {
  let matches: ApiMatch[] = [];
  let error = false;

  try {
    const data = await fetchMatches({ limit: 10, sort_by: "confidence_score", order: "desc" });
    matches = data.items.filter((m) => m.confidence_score !== null);
  } catch {
    error = true;
  }

  const unlockedMatches = matches.slice(0, FREE_SLOTS);
  const lockedMatches = matches.slice(FREE_SLOTS);

  const avgConfidence =
    unlockedMatches.length > 0
      ? Math.round(unlockedMatches.reduce((s, m) => s + (m.confidence_score ?? 0), 0) / unlockedMatches.length)
      : 0;

  return (
    <div className="flex min-h-screen bg-[#06090F] text-[#DDD5C4]">
      {/* Sidebar */}
      <aside className="hidden md:flex flex-col w-[220px] min-h-screen border-r border-[#1E2D42] bg-[#0A1220] px-4 py-6 gap-6 shrink-0">
        <Link href="/" className="flex items-center gap-2 font-bold text-lg mb-2">
          <RushPlayLogo />
          RushPlay
        </Link>

        <nav className="flex flex-col gap-1">
          {[
            { label: "Dashboard", href: "/dashboard", active: true },
            { label: "Historique", href: "/historique", active: false },
            { label: "Tarifs", href: "/#pricing", active: false },
          ].map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors"
              style={{
                background: item.active ? "rgba(200,240,0,0.10)" : "transparent",
                color: item.active ? "#C8F000" : "#7A8FA8",
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="mt-auto">
          <UserPlan />
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header className="flex items-center justify-between border-b border-[#1E2D42] px-6 py-4">
          <div>
            <div className="text-lg font-bold" style={{ fontFamily: "var(--font-heading, sans-serif)" }}>
              Signaux du jour
            </div>
            <div className="text-xs text-[#7A8FA8] font-[family-name:var(--font-mono)]">
              {new Date().toLocaleDateString("fr-FR", {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </div>
          </div>
          <Link href="/" className="text-sm text-[#7A8FA8] hover:text-[#DDD5C4] transition-colors">
            ← Accueil
          </Link>
        </header>

        <main className="flex-1 p-6 flex flex-col gap-6">
          {/* KPIs */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Précision algo", value: "57.6%", icon: <TrendingUpIcon className="size-4" /> },
              { label: "Signaux actifs", value: String(matches.length), icon: <ZapIcon className="size-4" /> },
              { label: "Confiance moy.", value: avgConfidence ? `${avgConfidence}%` : "—", icon: <TrendingUpIcon className="size-4" /> },
              { label: "Ligues couvertes", value: String(new Set(matches.map((m) => m.league)).size), icon: <ZapIcon className="size-4" /> },
            ].map((kpi) => (
              <div key={kpi.label} className="rounded-xl border border-[#1E2D42] bg-[#0E1828] p-4 flex flex-col gap-2">
                <div className="flex items-center gap-1.5 text-[#7A8FA8] text-xs">
                  <span style={{ color: "#C8F000" }}>{kpi.icon}</span>
                  {kpi.label}
                </div>
                <div className="text-2xl font-semibold font-[family-name:var(--font-mono)]" style={{ color: "#C8F000" }}>
                  {kpi.value}
                </div>
              </div>
            ))}
          </div>

          {error && (
            <div className="rounded-xl border border-[#f87171] bg-[rgba(248,113,113,0.08)] p-4 text-sm text-[#f87171]">
              Impossible de charger les données. Vérifiez votre connexion.
            </div>
          )}

          {!error && matches.length === 0 && (
            <div className="rounded-xl border border-[#1E2D42] bg-[#0E1828] p-8 text-center text-[#7A8FA8] text-sm">
              Aucun signal disponible pour le moment. Les analyses sont générées chaque matin à 8h.
            </div>
          )}

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

              <div className="text-xs text-[#7A8FA8] leading-relaxed px-1">
                RushPlay est un outil d&apos;analyse statistique. Aucun gain garanti. Jouez responsable — aide : 09 74 75 13 13
              </div>
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
}
