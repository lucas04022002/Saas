export const dynamic = "force-dynamic";

import FooterSection from "../../components/sections/footer/default";
import Navbar from "../../components/sections/navbar/default";
import HistoriqueClient from "../../components/ui/historique-client";
import { ApiAnalysis, fetchAnalyses } from "../../lib/api";

export default async function HistoriquePage() {
  let analyses: ApiAnalysis[] = [];
  let error = false;

  try {
    analyses = await fetchAnalyses();
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

        {!error && analyses.length > 0 && (
          <HistoriqueClient analyses={analyses} />
        )}
      </main>

      <FooterSection />
    </div>
  );
}
