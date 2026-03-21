import Link from "next/link";

import RushPlayLogo from "../../components/logos/rushplay";
import { mockMatches } from "../../data/mock";

const riskColors = {
  faible: { border: "#4ade80", bg: "rgba(34,197,94,0.10)", text: "#4ade80" },
  modéré: { border: "#eab308", bg: "rgba(234,179,8,0.10)", text: "#eab308" },
  élevé: { border: "#f87171", bg: "rgba(248,113,113,0.10)", text: "#f87171" },
};

const historique = [
  ...mockMatches.map((m) => ({ ...m, date: "19 mars 2026", resultat: "✓ Correct" })),
  ...mockMatches.slice(0, 3).map((m) => ({ ...m, id: m.id + 10, date: "18 mars 2026", resultat: "✗ Incorrect" })),
];

export default function HistoriquePage() {
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
          <div className="rounded-xl border border-[#1E2D42] bg-[#0E1828] p-4 flex flex-col gap-3">
            <div className="text-xs text-[#7A8FA8] font-medium uppercase tracking-wide">Plan actuel</div>
            <div className="font-bold text-[#DDD5C4]">Starter</div>
            <Link
              href="/#pricing"
              className="mt-1 inline-flex items-center justify-center rounded-md px-3 py-1.5 text-xs font-semibold"
              style={{ background: "#C8F000", color: "#06090F" }}
            >
              Passer Pro
            </Link>
          </div>
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
              Résultats des analyses passées
            </div>
          </div>
          <Link href="/" className="text-sm text-[#7A8FA8] hover:text-[#DDD5C4] transition-colors">
            ← Accueil
          </Link>
        </header>

        <main className="flex-1 p-6 flex flex-col gap-4">
          {Object.entries(
            historique.reduce<Record<string, typeof historique>>((acc, m) => {
              acc[m.date] = acc[m.date] || [];
              acc[m.date].push(m);
              return acc;
            }, {})
          ).map(([date, matches]) => (
            <div key={date} className="flex flex-col gap-2">
              <div className="text-xs text-[#7A8FA8] uppercase tracking-wide font-semibold mb-1">{date}</div>
              {matches.map((match) => {
                const colors = riskColors[match.risk];
                const correct = match.resultat.startsWith("✓");
                return (
                  <div
                    key={match.id}
                    className="rounded-xl border border-[#1E2D42] bg-[#0E1828] p-4 flex items-center gap-4"
                    style={{ borderLeft: `3px solid ${colors.border}` }}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-bold text-[#DDD5C4] truncate" style={{ fontFamily: "var(--font-heading, sans-serif)" }}>
                        {match.home} vs {match.away}
                      </div>
                      <div className="text-xs text-[#7A8FA8]">{match.league} · {match.time}</div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="font-[family-name:var(--font-mono)] font-semibold" style={{ color: "#C8F000" }}>
                        +{match.divergence}%
                      </span>
                      <span
                        className="text-xs px-2 py-0.5 rounded font-medium"
                        style={{ background: colors.bg, color: colors.text }}
                      >
                        {match.risk}
                      </span>
                      <span
                        className="text-xs font-semibold"
                        style={{ color: correct ? "#4ade80" : "#f87171" }}
                      >
                        {match.resultat}
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
