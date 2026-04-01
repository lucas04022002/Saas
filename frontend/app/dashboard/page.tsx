export const dynamic = "force-dynamic";

import FooterSection from "../../components/sections/footer/default";
import Navbar from "../../components/sections/navbar/default";
import DashboardClient from "../../components/ui/dashboard-client";
import { ApiMatch, fetchMatches } from "../../lib/api";

export default async function DashboardPage() {
  let matches: ApiMatch[] = [];
  let error = false;

  try {
    const data = await fetchMatches({
      limit: 20,
      sort_by: "confidence_score",
      order: "desc",
    });
    matches = data.items.filter((m) => m.confidence_score !== null);
  } catch {
    error = true;
  }

  const avgConfidence =
    matches.length > 0
      ? Math.round(
          matches.reduce((s, m) => s + (m.confidence_score ?? 0), 0) /
            matches.length,
        )
      : 0;

  return (
    <div className="min-h-screen bg-[#10131a] text-white">
      <Navbar activePath="/dashboard" />

      <main className="pt-16">
        {error && (
          <div className="max-w-7xl mx-auto px-6 pt-6">
            <div className="rounded-xl border border-[#f87171]/30 bg-[rgba(248,113,113,0.06)] p-4 text-sm text-[#f87171]">
              Impossible de charger les données. Le serveur est peut-être en
              train de démarrer (jusqu&apos;à 30s sur Render).
            </div>
          </div>
        )}

        {!error && matches.length === 0 && (
          <div className="max-w-7xl mx-auto px-6 pt-6">
            <div className="rounded-xl border border-[#454933]/20 bg-[#16191f] p-8 text-center text-slate-500 text-sm">
              Aucun signal disponible. Les analyses sont générées chaque matin à
              8h.
            </div>
          </div>
        )}

        {!error && matches.length > 0 && (
          <DashboardClient matches={matches} avgConfidence={avgConfidence} />
        )}
      </main>

      <FooterSection />
    </div>
  );
}
