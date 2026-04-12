"use client";

import { useMemo, useState } from "react";

import { ApiMatch, riskColors, riskLabel } from "@/lib/api";
import TeamLogo from "./team-logo";

interface DashboardClientProps {
  matches: ApiMatch[];
  todayMatches: ApiMatch[];
  avgConfidence: number;
  isPro: boolean;
}

export default function DashboardClient({
  matches,
  todayMatches,
  avgConfidence,
  isPro,
}: DashboardClientProps) {
  const [selectedLeague, setSelectedLeague] = useState<string>("all");
  const [minConfidence, setMinConfidence] = useState<number>(0);
  const [search, setSearch] = useState<string>("");

  const leagues = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const m of matches) {
      counts[m.league] = (counts[m.league] ?? 0) + 1;
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [matches]);

  const baseMatches = search.trim() ? matches : todayMatches;

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return baseMatches.filter((m) => {
      const leagueOk = selectedLeague === "all" || m.league === selectedLeague;
      const confOk = (m.confidence_score ?? 0) >= minConfidence;
      const searchOk = !q || m.home_team.toLowerCase().includes(q) || m.away_team.toLowerCase().includes(q);
      return leagueOk && confOk && searchOk;
    });
  }, [baseMatches, selectedLeague, minConfidence, search]);

  const FREE_SLOTS = 2;
  const visibleMatches = isPro ? filtered : filtered.slice(0, FREE_SLOTS);
  const lockedCount = isPro ? 0 : Math.max(0, filtered.length - FREE_SLOTS);

  const kpis = [
    { label: "Win Rate Global", value: "57.6%", sub: "↑ 2.4%", highlight: true, pulse: false },
    { label: "ROI Mensuel", value: "+12.4%", sub: "Moyenne", highlight: false, pulse: false },
    {
      label: "Confiance Moyenne",
      value: avgConfidence ? `${avgConfidence}%` : "—",
      sub: "Signaux du jour",
      highlight: false,
      pulse: false,
    },
    {
      label: "Signaux Actifs",
      value: String(matches.length),
      sub: null,
      highlight: true,
      pulse: true,
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="glass-card rounded-xl border border-[#454933]/20 p-5"
          >
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-1 font-bold">
              {kpi.label}
            </p>
            <div className="flex items-end gap-2">
              <span
                className={`text-3xl font-black ${kpi.highlight ? "text-[#c8f000]" : "text-white"}`}
                style={{ fontFamily: "var(--font-heading, sans-serif)" }}
              >
                {kpi.value}
              </span>
              {kpi.pulse && (
                <span className="w-3 h-3 rounded-full bg-[#c8f000] animate-pulse mb-1 ml-1" />
              )}
              {kpi.sub && (
                <span className="text-slate-500 text-sm mb-1">{kpi.sub}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Sidebar */}
        <aside className="lg:col-span-3 space-y-6">
          {/* Search — PRO only */}
          {isPro && (
            <div className="bg-[#16191f] p-4 rounded-xl">
              <input
                type="text"
                placeholder="Rechercher une équipe..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-[#32353c] rounded-lg text-sm text-white py-2.5 px-4 focus:ring-1 focus:ring-[#c8f000] outline-none placeholder-slate-600 border-none"
              />
            </div>
          )}
          {!isPro && (
            <div className="bg-[#16191f] p-4 rounded-xl flex items-center gap-3">
              <span className="text-slate-600 text-xs">🔒 Recherche réservée aux membres Pro</span>
            </div>
          )}

          {/* Ligues */}
          <div className="bg-[#16191f] p-6 rounded-xl space-y-3">
            <h3
              className="font-bold text-white text-lg"
              style={{ fontFamily: "var(--font-heading, sans-serif)" }}
            >
              Ligues
            </h3>
            <button
              onClick={() => setSelectedLeague("all")}
              className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors text-sm font-semibold ${
                selectedLeague === "all"
                  ? "bg-[#32353c]/50 text-white border-l-4 border-[#c8f000]"
                  : "text-slate-400 hover:bg-[#32353c]/30"
              }`}
            >
              <span>Toutes les ligues</span>
              <span className="text-xs opacity-60">{matches.length}</span>
            </button>
            {leagues.map(([league, count]) => (
              <button
                key={league}
                onClick={() => setSelectedLeague(league)}
                className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors text-sm font-semibold ${
                  selectedLeague === league
                    ? "bg-[#32353c]/50 text-white border-l-4 border-[#c8f000]"
                    : "text-slate-400 hover:bg-[#32353c]/30"
                }`}
              >
                <span className="truncate text-left">{league}</span>
                <span className="text-xs opacity-60 shrink-0 ml-2">{count}</span>
              </button>
            ))}
          </div>

          {/* AI Filter */}
          <div className="bg-[#16191f] p-6 rounded-xl">
            <h3
              className="font-bold text-white text-lg mb-4"
              style={{ fontFamily: "var(--font-heading, sans-serif)" }}
            >
              AI Filter
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Confiance Min.</span>
                <span className="text-[#c8f000] font-bold">{minConfidence}%</span>
              </div>
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
          </div>
        </aside>

        {/* Signal Feed */}
        <div className="lg:col-span-9">
          <div className="flex items-center gap-3 mb-6">
            <h2
              className="font-black text-2xl text-white"
              style={{ fontFamily: "var(--font-heading, sans-serif)" }}
            >
              Signaux Live
            </h2>
            <span className="bg-[#c8f000] text-[#2a3400] text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">
              Temps Réel
            </span>
          </div>


          {filtered.length === 0 && (
            <div className="rounded-xl border border-[#454933]/20 bg-[#16191f] p-8 text-center text-slate-500 text-sm">
              Aucun signal ne correspond aux filtres sélectionnés.
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Visible cards */}
            {visibleMatches.map((match) => {
              const colors = riskColors(match.risk_level);
              return (
                <div
                  key={match.id}
                  className="bg-[#1d2027] rounded-xl overflow-hidden border border-[#454933]/15 hover:border-[#c8f000]/30 transition-all duration-300 group"
                >
                  {/* Card header */}
                  <div className="px-5 py-3 border-b border-[#454933]/10 flex justify-between items-center bg-[#272a31]/40">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ background: colors.text }}
                      />
                      <span className="text-xs text-slate-400 uppercase tracking-widest">
                        {riskLabel(match.risk_level)}
                      </span>
                    </div>
                    {match.value_percent != null && (
                      <span
                        className="text-[11px] px-3 py-1 rounded-full font-bold border"
                        style={{
                          background: colors.bg,
                          color: colors.text,
                          borderColor: `${colors.text}30`,
                        }}
                      >
                        VALEUR +{match.value_percent.toFixed(1)}%
                      </span>
                    )}
                  </div>

                  {/* Teams */}
                  <div className="p-5">
                    <div className="flex justify-between items-center mb-5">
                      <div className="text-center flex-1">
                        <div className="w-12 h-12 mx-auto mb-2 flex items-center justify-center">
                          <TeamLogo name={match.home_team} size={40} />
                        </div>
                        <p className="font-bold text-sm text-white truncate">
                          {match.home_team}
                        </p>
                      </div>
                      <div className="px-4 text-center">
                        <p
                          className="font-black text-xl text-white"
                          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                        >
                          vs
                        </p>
                        <p className="text-xs text-slate-500 mt-1">{match.league}</p>
                      </div>
                      <div className="text-center flex-1">
                        <div className="w-12 h-12 mx-auto mb-2 flex items-center justify-center">
                          <TeamLogo name={match.away_team} size={40} />
                        </div>
                        <p className="font-bold text-sm text-white truncate">
                          {match.away_team}
                        </p>
                      </div>
                    </div>

                    {/* Conseil + Confiance */}
                    <div className="grid grid-cols-2 gap-3 mb-5">
                      <div className="bg-[#16191f] p-3 rounded-lg">
                        <p className="text-[10px] text-slate-500 uppercase font-bold mb-1">
                          Conseil IA
                        </p>
                        <p className="text-white font-bold text-sm truncate">
                          {match.recommended_bet ?? "—"}
                        </p>
                      </div>
                      <div className="bg-[#16191f] p-3 rounded-lg text-right">
                        <p className="text-[10px] text-slate-500 uppercase font-bold mb-1">
                          Confiance
                        </p>
                        <p className="text-[#c8f000] font-bold text-sm">
                          {match.confidence_score?.toFixed(0) ?? "—"}%
                        </p>
                      </div>
                    </div>

                    <a
                      href={`/signal/${match.id}`}
                      className="block w-full py-3 bg-[#c8f000] text-[#2a3400] font-black text-sm text-center rounded-xl group-hover:brightness-110 transition-all shadow-[0_4px_12px_rgba(200,240,0,0.15)]"
                      style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                    >
                      VOIR LE SIGNAL
                    </a>
                  </div>
                </div>
              );
            })}

            {/* Locked cards pour Starter */}
            {!isPro &&
              lockedCount > 0 &&
              Array.from({ length: Math.min(lockedCount, 2) }).map((_, i) => (
                <div
                  key={`locked-${i}`}
                  className="bg-[#1d2027] rounded-xl overflow-hidden border border-[#454933]/15 relative"
                >
                  <div className="absolute inset-0 bg-[#10131a]/70 backdrop-blur-[4px] z-10 flex flex-col items-center justify-center p-6 text-center">
                    <div className="text-3xl mb-3">🔒</div>
                    <h4
                      className="text-white font-bold mb-2"
                      style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                    >
                      Signal Premium
                    </h4>
                    <p className="text-slate-400 text-xs mb-5">
                      Réservé aux membres PRO. Débloquez pour accéder aux cotes
                      et analyses.
                    </p>
                    <a
                      href="/signup?plan=pro"
                      className="bg-[#c8f000] text-[#2a3400] px-5 py-2 rounded-lg font-extrabold text-sm hover:brightness-110 transition-all"
                      style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                    >
                      Débloquer maintenant
                    </a>
                  </div>
                  <div className="p-5 opacity-20 pointer-events-none">
                    <div className="h-5 bg-[#32353c] rounded w-1/2 mb-4" />
                    <div className="h-20 bg-[#32353c] rounded-lg mb-4" />
                    <div className="h-10 bg-[#32353c] rounded-xl" />
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
