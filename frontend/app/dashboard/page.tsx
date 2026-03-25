export const dynamic = "force-dynamic";

import { TrendingUpIcon, ZapIcon } from "lucide-react";
import Link from "next/link";

import RushPlayLogo from "../../components/logos/rushplay";
import MatchList from "../../components/ui/match-list";
import UserPlan from "../../components/ui/user-plan";
import { ApiMatch, fetchMatches } from "../../lib/api";

export default async function DashboardPage() {
  let matches: ApiMatch[] = [];
  let error = false;

  try {
    const data = await fetchMatches({ limit: 10, sort_by: "confidence_score", order: "desc" });
    matches = data.items.filter((m) => m.confidence_score !== null);
  } catch {
    error = true;
  }

  const avgConfidence =
    matches.length > 0
      ? Math.round(matches.reduce((s, m) => s + (m.confidence_score ?? 0), 0) / matches.length)
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

          <MatchList matches={matches} />
        </main>
      </div>
    </div>
  );
}
