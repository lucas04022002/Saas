export const dynamic = "force-dynamic";

import { notFound } from "next/navigation";
import FooterSection from "../../../components/sections/footer/default";
import Navbar from "../../../components/sections/navbar/default";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SignalData {
  match: {
    id: string;
    home_team: string;
    away_team: string;
    league: string;
    country: string;
    kickoff_at: string;
    status: string;
  };
  analysis: {
    confidence_score: number;
    recommended_bet: string;
    bookmaker_odds: number;
    value_percent: number;
    risk_level: "LOW" | "MEDIUM" | "HIGH";
    ai_explanation: string;
    updated_at: string;
  };
  warning_points: string[];
  home_form: string | null;
  away_form: string | null;
}

async function fetchSignal(matchId: string): Promise<SignalData | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/signal/${matchId}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    const json = await res.json();
    return json.data;
  } catch {
    return null;
  }
}

function riskConfig(level: "LOW" | "MEDIUM" | "HIGH") {
  const map = {
    LOW: { label: "Faible", color: "#4ade80", bg: "rgba(34,197,94,0.12)" },
    MEDIUM: { label: "Modéré", color: "#eab308", bg: "rgba(234,179,8,0.12)" },
    HIGH: { label: "Élevé", color: "#f87171", bg: "rgba(248,113,113,0.12)" },
  };
  return map[level];
}

function FormBadge({ result }: { result: string }) {
  const map: Record<string, { bg: string; text: string }> = {
    W: { bg: "rgba(34,197,94,0.15)", text: "#4ade80" },
    D: { bg: "rgba(234,179,8,0.15)", text: "#eab308" },
    L: { bg: "rgba(248,113,113,0.15)", text: "#f87171" },
  };
  const style = map[result] ?? map["D"];
  return (
    <span
      className="inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold"
      style={{ background: style.bg, color: style.text }}
    >
      {result}
    </span>
  );
}

function FormRow({ label, form }: { label: string; form: string | null }) {
  if (!form) {
    return (
      <div className="flex items-center justify-between">
        <span className="text-slate-400 text-sm">{label}</span>
        <span className="text-slate-600 text-xs">Données indisponibles</span>
      </div>
    );
  }
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-400 text-sm">{label}</span>
      <div className="flex gap-1">
        {form.split("").map((r, i) => (
          <FormBadge key={i} result={r} />
        ))}
      </div>
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 62 ? "#4ade80" : value >= 52 ? "#eab308" : "#f87171";
  return (
    <div>
      <div className="flex justify-between mb-2">
        <span className="text-slate-400 text-sm">Confiance IA</span>
        <span className="font-bold" style={{ color }}>{value.toFixed(1)}%</span>
      </div>
      <div className="h-2 rounded-full bg-[#32353c] overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${value}%`, background: color }}
        />
      </div>
    </div>
  );
}

export default async function SignalPage({
  params,
}: {
  params: Promise<{ match_id: string }>;
}) {
  const { match_id } = await params;
  const data = await fetchSignal(match_id);
  if (!data) notFound();

  const { match, analysis, warning_points, home_form, away_form } = data;
  const risk = riskConfig(analysis.risk_level);
  const kickoff = new Date(match.kickoff_at);
  const valuePositive = analysis.value_percent >= 0;

  return (
    <div className="min-h-screen bg-[#10131a] text-white">
      <Navbar activePath="/dashboard" />

      <main className="pt-24 pb-16 px-6 max-w-3xl mx-auto">
        {/* Header */}
        <div className="glass-card rounded-2xl border border-[#454933]/20 p-8 mb-6">
          <div className="text-xs text-slate-500 mb-4 uppercase tracking-widest">
            {match.league} · {kickoff.toLocaleDateString("fr-FR", { day: "numeric", month: "long" })} à{" "}
            {kickoff.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
          </div>

          <div className="flex items-center justify-between gap-4 mb-6">
            <div className="flex-1 text-center">
              <div className="text-2xl font-black text-white">{match.home_team}</div>
              <div className="text-xs text-slate-500 mt-1">Domicile</div>
            </div>
            <div className="text-slate-600 font-bold text-xl">VS</div>
            <div className="flex-1 text-center">
              <div className="text-2xl font-black text-white">{match.away_team}</div>
              <div className="text-xs text-slate-500 mt-1">Extérieur</div>
            </div>
          </div>

          {/* Conseil principal */}
          <div className="rounded-xl bg-[#c8f000]/10 border border-[#c8f000]/20 p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-[#c8f000]/70 mb-1 uppercase tracking-wider">Conseil IA</div>
              <div className="text-lg font-black text-[#c8f000]">{analysis.recommended_bet}</div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-400 mb-1">Cote</div>
              <div className="text-2xl font-black text-white">{analysis.bookmaker_odds.toFixed(2)}</div>
            </div>
          </div>
        </div>

        {/* Stats clés */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="glass-card rounded-xl border border-[#454933]/20 p-4 text-center">
            <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Confiance</div>
            <div className="text-2xl font-black text-[#c8f000]">{analysis.confidence_score.toFixed(0)}%</div>
          </div>
          <div className="glass-card rounded-xl border border-[#454933]/20 p-4 text-center">
            <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Valeur</div>
            <div
              className="text-2xl font-black"
              style={{ color: valuePositive ? "#4ade80" : "#f87171" }}
            >
              {valuePositive ? "+" : ""}{analysis.value_percent.toFixed(1)}%
            </div>
          </div>
          <div className="glass-card rounded-xl border border-[#454933]/20 p-4 text-center">
            <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Risque</div>
            <div className="text-lg font-black" style={{ color: risk.color }}>{risk.label}</div>
          </div>
        </div>

        {/* Confiance bar + explication */}
        <div className="glass-card rounded-2xl border border-[#454933]/20 p-6 mb-6 space-y-5">
          <ConfidenceBar value={analysis.confidence_score} />

          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Analyse IA</div>
            <p className="text-slate-300 text-sm leading-relaxed">{analysis.ai_explanation}</p>
          </div>
        </div>

        {/* Forme des équipes */}
        <div className="glass-card rounded-2xl border border-[#454933]/20 p-6 mb-6">
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-5">5 Derniers Matchs</div>
          <div className="space-y-4">
            <FormRow label={match.home_team} form={home_form} />
            <FormRow label={match.away_team} form={away_form} />
          </div>
          <div className="mt-4 flex gap-3 text-xs text-slate-500">
            <span><span className="text-[#4ade80] font-bold">V</span> = Victoire</span>
            <span><span className="text-[#eab308] font-bold">N</span> = Nul</span>
            <span><span className="text-[#f87171] font-bold">D</span> = Défaite</span>
          </div>
        </div>

        {/* Points de vigilance */}
        {warning_points.length > 0 && (
          <div className="glass-card rounded-2xl border border-[#454933]/20 p-6 mb-6">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-4">Points de vigilance</div>
            <ul className="space-y-2">
              {warning_points.map((wp, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
                  <span className="text-[#eab308] mt-0.5">⚠</span>
                  {wp}
                </li>
              ))}
            </ul>
          </div>
        )}

        <a
          href="/dashboard"
          className="block w-full py-3 rounded-xl bg-[#32353c] text-slate-300 font-bold text-sm text-center hover:bg-[#c8f000] hover:text-[#2a3400] transition-all"
        >
          ← Retour au dashboard
        </a>
      </main>

      <FooterSection />
    </div>
  );
}
