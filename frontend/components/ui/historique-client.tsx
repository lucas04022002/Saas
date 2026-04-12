"use client";

import { useMemo, useState } from "react";

import { ApiAnalysis, riskColors, riskLabel } from "@/lib/api";

interface HistoriqueClientProps {
  analyses: ApiAnalysis[];
}

function getPredictionResult(a: ApiAnalysis): "win" | "loss" | null {
  if (a.home_score == null || a.away_score == null) return null;
  const h = a.home_score;
  const aw = a.away_score;
  const actual = h > aw ? "home" : h < aw ? "away" : "draw";
  const predicted = a.recommended_bet.toLowerCase().includes("domicile")
    ? "home"
    : a.recommended_bet.toLowerCase().includes("exterieur") || a.recommended_bet.toLowerCase().includes("extérieur")
    ? "away"
    : "draw";
  return actual === predicted ? "win" : "loss";
}

function formatShortDate(iso: string) {
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "short",
  });
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function HistoriqueClient({ analyses }: HistoriqueClientProps) {
  const [period, setPeriod] = useState<"7J" | "30J" | "ALL">("30J");
  const [selectedLeague, setSelectedLeague] = useState<string>("all");
  const [minConfidence, setMinConfidence] = useState<number>(0);

  const sorted = useMemo(() => {
    return [...analyses].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [analyses]);

  const periodFiltered = useMemo(() => {
    if (period === "ALL") return sorted;
    const days = period === "7J" ? 7 : 30;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    return sorted.filter((a) => new Date(a.created_at) >= cutoff);
  }, [sorted, period]);

  const leagues = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const a of sorted) {
      const league = a.league ?? "Football";
      counts[league] = (counts[league] ?? 0) + 1;
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [sorted]);

  const filtered = useMemo(() => {
    return periodFiltered.filter((a) => {
      const league = a.league ?? "Football";
      const leagueOk = selectedLeague === "all" || league === selectedLeague;
      const confOk = a.confidence_score >= minConfidence;
      return leagueOk && confOk;
    });
  }, [periodFiltered, selectedLeague, minConfidence]);

  // Stats
  const totalSignaux = filtered.length;
  const avgConfidence =
    filtered.length > 0
      ? Math.round(filtered.reduce((s, a) => s + a.confidence_score, 0) / filtered.length)
      : 0;
  const bestValue =
    filtered.length > 0
      ? Math.max(...filtered.map((a) => a.value_percent))
      : 0;

  // Bar chart: last 20 analyses confidence scores
  const chartData = useMemo(() => {
    return filtered.slice(0, 20).reverse();
  }, [filtered]);

  const maxConf = Math.max(...chartData.map((a) => a.confidence_score), 1);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Stats Header + Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-10">
        {/* Stats */}
        <div className="lg:col-span-4 grid grid-cols-2 gap-4">
          <div className="bg-[#1d2027] rounded-xl p-6 flex flex-col justify-center">
            <span className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-bold">
              Total Signaux
            </span>
            <span
              className="text-4xl font-black text-white"
              style={{ fontFamily: "var(--font-heading, sans-serif)" }}
            >
              {totalSignaux}
            </span>
            <div className="mt-3 text-xs text-slate-500">
              {period === "ALL" ? "Depuis le début" : `Sur les ${period === "7J" ? "7" : "30"} derniers jours`}
            </div>
          </div>

          <div className="bg-[#1d2027] rounded-xl p-6 flex flex-col justify-center border-l-4 border-[#c8f000]">
            <span className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-bold">
              Confiance Moy.
            </span>
            <span
              className="text-4xl font-black text-[#c8f000]"
              style={{ fontFamily: "var(--font-heading, sans-serif)" }}
            >
              {avgConfidence}%
            </span>
            <div className="mt-3 text-xs text-slate-500">Score moyen</div>
          </div>

          <div className="bg-[#1d2027] rounded-xl p-6 flex flex-col justify-center col-span-2">
            <span className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-bold">
              Meilleure Valeur
            </span>
            <div className="flex items-baseline gap-2">
              <span
                className="text-4xl font-black text-white"
                style={{ fontFamily: "var(--font-heading, sans-serif)" }}
              >
                +{bestValue.toFixed(1)}%
              </span>
            </div>
            <div className="mt-2 h-1 w-full bg-[#32353c] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#c8f000] rounded-full transition-all duration-700"
                style={{ width: `${Math.min(bestValue, 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Chart */}
        <div className="lg:col-span-8 bg-[#16191f] rounded-xl p-6 relative overflow-hidden group">
          <div className="flex justify-between items-center mb-6">
            <h3
              className="font-bold text-xl text-white"
              style={{ fontFamily: "var(--font-heading, sans-serif)" }}
            >
              Courbe de Confiance
            </h3>
            <div className="flex gap-2">
              {(["7J", "30J", "ALL"] as const).map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                    period === p
                      ? "bg-[#c8f000] text-[#2a3400]"
                      : "bg-[#32353c] text-slate-400 hover:text-white"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {chartData.length === 0 ? (
            <div className="h-40 flex items-center justify-center text-slate-500 text-sm">
              Aucune donnée sur cette période
            </div>
          ) : (
            <div className="relative h-40 w-full flex items-end gap-1">
              {chartData.map((a, i) => {
                const pct = (a.confidence_score / maxConf) * 100;
                const colors = riskColors(a.risk_level);
                return (
                  <div
                    key={a.match_id + i}
                    className="flex-1 rounded-t-sm transition-all duration-500 min-w-0"
                    style={{
                      height: `${Math.max(pct, 8)}%`,
                      background:
                        a.confidence_score >= 70
                          ? `rgba(200,240,0,${0.3 + (pct / 100) * 0.7})`
                          : `${colors.bg}`,
                    }}
                    title={`${a.home_team} vs ${a.away_team} — ${a.confidence_score.toFixed(0)}%`}
                  />
                );
              })}
              <div className="absolute inset-0 bg-gradient-to-t from-[#16191f] to-transparent pointer-events-none" />
            </div>
          )}

          <div className="absolute -right-10 -top-10 w-40 h-40 bg-[#c8f000]/5 rounded-full blur-3xl animate-pulse pointer-events-none" />
        </div>
      </div>

      {/* Filters */}
      <div className="bg-[#1d2027] rounded-xl p-4 mb-6 flex flex-wrap gap-4 items-end border border-[#454933]/15">
        <div className="flex-1 min-w-[180px]">
          <label className="block text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-bold">
            Ligue
          </label>
          <select
            value={selectedLeague}
            onChange={(e) => setSelectedLeague(e.target.value)}
            className="w-full bg-[#32353c] border-none rounded-lg text-sm text-white py-2.5 px-4 focus:ring-1 focus:ring-[#c8f000] outline-none cursor-pointer"
          >
            <option value="all">Toutes les ligues ({sorted.length})</option>
            {leagues.map(([league, count]) => (
              <option key={league} value={league}>
                {league} ({count})
              </option>
            ))}
          </select>
        </div>

        <div className="w-56">
          <label className="block text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-bold">
            Confiance Min. — <span className="text-[#c8f000]">{minConfidence}%</span>
          </label>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={minConfidence}
            onChange={(e) => setMinConfidence(Number(e.target.value))}
            className="w-full h-1 rounded-lg appearance-none cursor-pointer accent-[#c8f000]"
            style={{
              background: `linear-gradient(to right, #c8f000 ${minConfidence}%, #32353c ${minConfidence}%)`,
            }}
          />
        </div>

        <div className="text-xs text-slate-500 self-end pb-2">
          {filtered.length} signal{filtered.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* Table */}
      <div className="bg-[#16191f] rounded-xl overflow-hidden border border-[#454933]/15">
        {filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            Aucun signal ne correspond aux filtres sélectionnés.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-[#272a31]/50 text-[10px] uppercase tracking-widest text-slate-500">
                  <th className="px-6 py-4 font-bold">Date</th>
                  <th className="px-6 py-4 font-bold">Événement</th>
                  <th className="px-6 py-4 font-bold text-center">Score</th>
                  <th className="px-6 py-4 font-bold">Conseil IA</th>
                  <th className="px-6 py-4 font-bold text-center">Résultat</th>
                  <th className="px-6 py-4 font-bold text-center">Confiance</th>
                  <th className="px-6 py-4 font-bold text-center">Cotes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#32353c]/30">
                {filtered.map((a) => {
                  const hasScore = a.home_score != null && a.away_score != null;
                  const predResult = hasScore ? getPredictionResult(a) : null;
                  return (
                    <tr
                      key={a.match_id}
                      className="hover:bg-[#272a31]/30 transition-colors"
                    >
                      <td className="px-6 py-5">
                        <div className="text-sm font-medium text-white">
                          {formatShortDate(a.kickoff_at ?? a.created_at)}
                        </div>
                        <div className="text-xs text-slate-500">
                          {formatTime(a.kickoff_at ?? a.created_at)}
                        </div>
                      </td>

                      <td className="px-6 py-5">
                        <div
                          className="text-sm font-bold text-white"
                          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                        >
                          {a.home_team} vs {a.away_team}
                        </div>
                        <div className="text-xs text-slate-500">
                          {a.league ?? "Football"}
                        </div>
                      </td>

                      <td className="px-6 py-5 text-center">
                        {hasScore ? (
                          <span className="font-black text-white text-base">
                            {a.home_score} - {a.away_score}
                          </span>
                        ) : (
                          <span className="text-slate-600 text-xs">—</span>
                        )}
                      </td>

                      <td className="px-6 py-5 text-sm text-slate-300">
                        {a.recommended_bet}
                      </td>

                      <td className="px-6 py-5 text-center">
                        {predResult === "win" && (
                          <span className="px-3 py-1 rounded-full text-[10px] font-bold bg-[rgba(34,197,94,0.15)] text-[#4ade80]">✓ Gagné</span>
                        )}
                        {predResult === "loss" && (
                          <span className="px-3 py-1 rounded-full text-[10px] font-bold bg-[rgba(248,113,113,0.15)] text-[#f87171]">✗ Perdu</span>
                        )}
                        {predResult === null && (
                          <span className="text-slate-600 text-xs">—</span>
                        )}
                      </td>

                      <td className="px-6 py-5 text-center">
                        <span className="font-bold text-[#c8f000] text-sm">
                          {a.confidence_score.toFixed(0)}%
                        </span>
                      </td>

                      <td className="px-6 py-5 text-center">
                        <span className="font-bold text-white text-sm">
                          {a.bookmaker_odds.toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
