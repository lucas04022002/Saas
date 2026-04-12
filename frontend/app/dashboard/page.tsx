export const dynamic = "force-dynamic";

import { cookies } from "next/headers";
import FooterSection from "../../components/sections/footer/default";
import Navbar from "../../components/sections/navbar/default";
import DashboardClient from "../../components/ui/dashboard-client";
import { ApiMatch, fetchMatches } from "../../lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default async function DashboardPage() {
  let matches: ApiMatch[] = [];
  let error = false;
  let isPro = false;

  let todayMatches: ApiMatch[] = [];

  // Vérifier le plan côté serveur
  const cookieStore = await cookies();
  const token = cookieStore.get("rushplay_token")?.value;
  if (token) {
    try {
      const meRes = await fetch(`${API_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
      const me = await meRes.json();
      const plan = me?.data?.subscription_plan ?? "STARTER";
      isPro = plan === "PRO" || plan === "ELITE";
    } catch {
      // STARTER par défaut
    }
  }

  try {
    const now = new Date();
    const in4Days = new Date(now);
    in4Days.setDate(in4Days.getDate() + 4);
    const in7Days = new Date(now);
    in7Days.setDate(in7Days.getDate() + 7);

    const allData = await fetchMatches({ limit: 100, sort_by: "kickoff_at", order: "asc", status: "SCHEDULED" });

    const allFiltered = allData.items.filter((m) => m.confidence_score !== null);

    todayMatches = allFiltered
      .filter((m) => new Date(m.kickoff_at) <= in4Days)
      .sort((a, b) => (b.confidence_score ?? 0) - (a.confidence_score ?? 0));

    matches = allFiltered.filter((m) => new Date(m.kickoff_at) <= in7Days);
  } catch {
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
          <DashboardClient matches={matches} todayMatches={todayMatches} avgConfidence={avgConfidence} isPro={isPro} />
        )}
      </main>

      <FooterSection />
    </div>
  );
}
