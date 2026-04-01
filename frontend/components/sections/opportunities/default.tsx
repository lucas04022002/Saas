const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "https://saas-oi6c.onrender.com";

interface Opportunity {
  match_id: string;
  home_team: string;
  away_team: string;
  league: string;
  confidence_score: number;
  recommended_bet: string;
  bookmaker_odds: number;
  value_percent: number;
  risk_level: string;
}

async function fetchTopOpportunities(): Promise<Opportunity[]> {
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/v1/opportunities/top?limit=3`,
      { next: { revalidate: 3600 } },
    );
    if (!res.ok) return [];
    const json = await res.json();
    return json.data ?? [];
  } catch {
    return [];
  }
}

function riskColor(risk: string) {
  if (risk === "faible") return { bg: "rgba(34,197,94,0.12)", text: "#4ade80" };
  if (risk === "élevé") return { bg: "rgba(239,68,68,0.12)", text: "#f87171" };
  return { bg: "rgba(234,179,8,0.12)", text: "#eab308" };
}

function SignalCard({ opp }: { opp: Opportunity }) {
  const risk = riskColor(opp.risk_level);
  return (
    <div className="glass-card rounded-xl border border-[#454933]/20 p-6 hover:border-[#c8f000]/30 transition-all group">
      <div className="flex justify-between items-start mb-6">
        <span className="px-3 py-1 bg-[#c8f000]/10 text-[#c8f000] text-[10px] font-bold uppercase tracking-widest rounded-full">
          Haute Confiance
        </span>
        <span
          className="text-xs px-2 py-0.5 rounded font-semibold"
          style={{ background: risk.bg, color: risk.text }}
        >
          {opp.risk_level}
        </span>
      </div>
      <div className="flex items-center justify-between mb-6">
        <div className="text-center flex-1">
          <div className="text-sm font-bold text-white truncate">{opp.home_team}</div>
          <div className="text-xs text-slate-500 mt-0.5">{opp.league}</div>
        </div>
        <div className="flex flex-col items-center px-4">
          <div className="text-xs text-slate-500 mb-1">
            Cote :{" "}
            <span className="text-white font-bold">
              {opp.bookmaker_odds.toFixed(2)}
            </span>
          </div>
          <div className="h-px w-16 bg-gradient-to-r from-transparent via-[#454933]/50 to-transparent" />
          <div className="text-[10px] text-[#c8f000] mt-1 font-bold">
            Value : +{opp.value_percent.toFixed(1)}%
          </div>
        </div>
        <div className="text-center flex-1">
          <div className="text-sm font-bold text-white truncate">{opp.away_team}</div>
          <div className="text-xs text-slate-500 mt-0.5">Extérieur</div>
        </div>
      </div>
      <div className="space-y-2 mb-6">
        <div className="flex justify-between text-sm">
          <span className="text-slate-400">Marché</span>
          <span className="text-white font-bold">{opp.recommended_bet}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-400">Probabilité IA</span>
          <span className="text-[#c8f000] font-bold">
            {opp.confidence_score.toFixed(1)}%
          </span>
        </div>
      </div>
      <a
        href="/dashboard"
        className="block w-full py-3 rounded-lg bg-[#32353c] text-slate-300 font-bold text-sm text-center group-hover:bg-[#c8f000] group-hover:text-[#2a3400] transition-all"
        style={{ fontFamily: "var(--font-heading, sans-serif)" }}
      >
        Voir le signal
      </a>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="glass-card rounded-xl border border-[#454933]/20 p-6 animate-pulse">
      <div className="h-5 bg-[#32353c] rounded w-1/2 mb-6" />
      <div className="h-24 bg-[#32353c] rounded-lg mb-6" />
      <div className="space-y-3">
        <div className="h-4 bg-[#32353c] rounded w-full" />
        <div className="h-4 bg-[#32353c] rounded w-2/3" />
      </div>
      <div className="h-10 bg-[#32353c] rounded-lg mt-6" />
    </div>
  );
}

function LockedCard() {
  return (
    <div className="glass-card rounded-xl border border-[#454933]/20 p-6 relative overflow-hidden">
      <div className="absolute inset-0 bg-[#32353c]/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center p-6 text-center">
        <div className="text-4xl mb-4">🔒</div>
        <h4
          className="text-white font-bold mb-2"
          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
        >
          Signal Pro Exclusive
        </h4>
        <p className="text-slate-400 text-xs mb-6">
          Ce signal est réservé aux membres de l&apos;abonnement Pro.
        </p>
        <a
          href="/signup?plan=pro"
          className="px-6 py-2 bg-[#c8f000] text-[#2a3400] rounded-lg font-extrabold text-sm hover:brightness-110 transition-all"
          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
        >
          Passer à RushPlay Pro
        </a>
      </div>
      <div className="opacity-20 pointer-events-none">
        <div className="h-6 bg-[#32353c] rounded-full w-2/3 mb-8" />
        <div className="h-24 bg-[#32353c] rounded-lg mb-6" />
        <div className="space-y-3">
          <div className="h-4 bg-[#32353c] rounded-full w-full" />
          <div className="h-4 bg-[#32353c] rounded-full w-1/2" />
        </div>
      </div>
    </div>
  );
}

export default async function Opportunities() {
  const opps = await fetchTopOpportunities();
  const visible = opps.slice(0, 2);

  return (
    <section className="py-24 px-6 bg-[#10131a]">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
          <div>
            <h2
              className="text-4xl md:text-5xl font-black text-white mb-4"
              style={{ fontFamily: "var(--font-heading, sans-serif)" }}
            >
              Signaux du jour
            </h2>
            <p className="text-slate-400 text-lg">
              Aperçu en temps réel des opportunités détectées.
            </p>
          </div>
          <div className="flex gap-2">
            {["Foot", "Tennis", "NBA"].map((sport) => (
              <span
                key={sport}
                className="px-4 py-2 bg-[#272a31] rounded-lg text-xs font-bold uppercase text-slate-400 border border-[#454933]/15"
              >
                {sport}
              </span>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {visible.map((opp) => (
            <SignalCard key={opp.match_id} opp={opp} />
          ))}
          {visible.length < 2 &&
            Array.from({ length: 2 - visible.length }).map((_, i) => (
              <SkeletonCard key={`skeleton-${i}`} />
            ))}
          <LockedCard />
        </div>
      </div>
    </section>
  );
}
