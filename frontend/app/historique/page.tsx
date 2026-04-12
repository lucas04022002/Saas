export const dynamic = "force-dynamic";

import { cookies } from "next/headers";
import FooterSection from "../../components/sections/footer/default";
import Navbar from "../../components/sections/navbar/default";
import HistoriqueClient from "../../components/ui/historique-client";
import { ApiAnalysis, fetchAnalyses } from "../../lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default async function HistoriquePage() {
  let analyses: ApiAnalysis[] = [];
  let error = false;
  let isPro = false;

  // Check plan
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
      // si erreur on considère STARTER
    }
  }

  try {
    analyses = await fetchAnalyses("FINISHED");
    if (!isPro) analyses = analyses.slice(0, 5);
  } catch {
    error = true;
  }

  return (
    <div className="min-h-screen bg-[#10131a] text-white">
      <Navbar activePath="/historique" />

      <main className="pt-16">
        {error && (
          <div className="max-w-7xl mx-auto px-6 pt-6">
            <div className="rounded-xl border border-[#f87171]/30 bg-[rgba(248,113,113,0.06)] p-4 text-sm text-[#f87171]">
              Impossible de charger l&apos;historique. Le serveur est peut-être en
              train de démarrer (jusqu&apos;à 30s sur Render).
            </div>
          </div>
        )}

        {!error && analyses.length === 0 && (
          <div className="max-w-7xl mx-auto px-6 pt-6">
            <div className="rounded-xl border border-[#454933]/20 bg-[#16191f] p-8 text-center text-slate-500 text-sm">
              Aucun signal dans l&apos;historique pour le moment.
            </div>
          </div>
        )}

        {!error && !isPro && analyses.length > 0 && (
          <div className="max-w-7xl mx-auto px-6 pt-6">
            <div className="rounded-xl border border-[#c8f000]/20 bg-[#c8f000]/5 p-4 text-sm text-[#c8f000] flex items-center justify-between">
              <span>Accès limité aux 5 derniers signaux. Passez Pro pour l&apos;historique complet.</span>
              <a href="/tarifs" className="bg-[#c8f000] text-[#2a3400] px-4 py-1.5 rounded-lg font-bold text-xs hover:brightness-110 transition-all">
                Passer Pro
              </a>
            </div>
          </div>
        )}

        {!error && analyses.length > 0 && (
          <HistoriqueClient analyses={analyses} />
        )}
      </main>

      <FooterSection />
    </div>
  );
}
