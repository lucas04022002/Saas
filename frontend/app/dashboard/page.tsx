export const dynamic = "force-dynamic";

import FooterSection from "../../components/sections/footer/default";
import Navbar from "../../components/sections/navbar/default";
import DashboardClient from "../../components/ui/dashboard-client";
import { ApiMatch, fetchMatches } from "../../lib/api";

export default async function DashboardPage() {
  let matches: ApiMatch[] = [];
  let error = false;

  let todayMatches: ApiMatch[] = [];

  try {
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const toDateStr = (d: Date) => d.toISOString().split("T")[0];

    const [todayData, tomorrowData, allData] = await Promise.all([
      fetchMatches({ limit: 50, sort_by: "confidence_score", order: "desc", date: toDateStr(now), status: "SCHEDULED" }),
      fetchMatches({ limit: 50, sort_by: "confidence_score", order: "desc", date: toDateStr(tomorrow), status: "SCHEDULED" }),
      fetchMatches({ limit: 100, sort_by: "kickoff_at", order: "asc", status: "SCHEDULED" }),
    ]);

    todayMatches = [...todayData.items, ...tomorrowData.items]
      .filter((m) => m.confidence_score !== null)
      .sort((a, b) => (b.confidence_score ?? 0) - (a.confidence_score ?? 0));

    matches = allData.items.filter((m) => m.confidence_score !== null);
  } catch (err) {
    console.error("[dashboard] fetch error:", err);
    error = true;
  }

  const avgConfidence =
    todayMatches.length > 0
      ? Math.round(
          todayMatches.reduce((s, m) => s + (m.confidence_score ?? 0), 0) /
            todayMatches.length,
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
          <DashboardClient matches={matches} todayMatches={todayMatches} avgConfidence={avgConfidence} />
        )}
      </main>

      <FooterSection />
    </div>
  );
}
