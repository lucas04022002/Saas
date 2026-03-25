export const dynamic = "force-dynamic";

import Link from "next/link";

import RushPlayLogo from "../../components/logos/rushplay";
import UserPlan from "../../components/ui/user-plan";
import { ApiAnalysis, fetchAnalyses, formatDate, riskColors, riskLabel } from "../../lib/api";

export default async function HistoriquePage() {
  let analyses: ApiAnalysis[] = [];
  let error = false;

  try {
    analyses = await fetchAnalyses();
  } catch {
    error = true;
  }

  // Grouper par date
  const grouped = analyses.reduce<Record<string, typeof analyses>>((acc, a) => {
    const date = formatDate(a.created_at);
    acc[date] = acc[date] || [];
    acc[date].push(a);
    return acc;
  }, {});

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
            { label: "Dashboard", href: "/dashboard", active: false },
            { label: "Historique", href: "/historique", active: true },
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
        <header className="flex items-center justify-between border-b border-[#1E2D42] px-6 py-4">
          <div>
            <div className="text-lg font-bold" style={{ fontFamily: "var(--font-heading, sans-serif)" }}>
              Historique des signaux
            </div>
            <div className="text-xs text-[#7A8FA8] font-[family-name:var(--font-mono)]">
              {analyses.length} analyse{analyses.length !== 1 ? "s" : ""} au total
            </div>
          </div>
          <Link href="/" className="text-sm text-[#7A8FA8] hover:text-[#DDD5C4] transition-colors">
            ← Accueil
          </Link>
        </header>

        <main className="flex-1 p-6 flex flex-col gap-4">
          {error && (
            <div className="rounded-xl border border-[#f87171] bg-[rgba(248,113,113,0.08)] p-4 text-sm text-[#f87171]">
              Impossible de charger l&apos;historique. Vérifiez votre connexion.
            </div>
          )}

          {!error && analyses.length === 0 && (
            <div className="rounded-xl border border-[#1E2D42] bg-[#0E1828] p-8 text-center text-[#7A8FA8] text-sm">
              Aucune analyse dans l&apos;historique pour le moment.
            </div>
          )}

          {Object.entries(grouped).map(([date, items]) => (
            <div key={date} className="flex flex-col gap-2">
              <div className="text-xs text-[#7A8FA8] uppercase tracking-wide font-semibold mb-1">{date}</div>
              {items.map((a) => {
                const colors = riskColors(a.risk_level);
                return (
                  <div
                    key={a.match_id}
                    className="rounded-xl border border-[#1E2D42] bg-[#0E1828] p-4 flex items-center gap-4"
                    style={{ borderLeft: `3px solid ${colors.border}` }}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-bold text-[#DDD5C4] truncate" style={{ fontFamily: "var(--font-heading, sans-serif)" }}>
                        {a.home_team} vs {a.away_team}
                      </div>
                      <div className="text-xs text-[#7A8FA8]">{a.recommended_bet}</div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="font-[family-name:var(--font-mono)] font-semibold" style={{ color: "#C8F000" }}>
                        +{a.value_percent.toFixed(1)}%
                      </span>
                      <span
                        className="text-xs px-2 py-0.5 rounded font-medium"
                        style={{ background: colors.bg, color: colors.text }}
                      >
                        {riskLabel(a.risk_level)}
                      </span>
                      <span className="text-xs text-[#7A8FA8] font-[family-name:var(--font-mono)]">
                        {a.confidence_score.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </main>
      </div>
    </div>
  );
}
