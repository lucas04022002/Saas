const STATS = [
  {
    value: "57.6%",
    label: "Précision Moyenne",
    description: "Basé sur les 10 000 derniers signaux générés par l'IA.",
    color: "text-[#c8f000]",
  },
  {
    value: "+12.4%",
    label: "ROI Mensuel Moyen",
    description: "Performance nette après frais de gestion de bankroll.",
    color: "text-slate-300",
  },
  {
    value: "24/7",
    label: "Analyse en Temps Réel",
    description: "Plus de 80 championnats scannés à chaque seconde.",
    color: "text-white",
  },
];

export default function Stats() {
  return (
    <section className="py-24 bg-[#0b0e14]">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 text-center md:text-left">
          {STATS.map((stat) => (
            <div key={stat.label} className="space-y-2">
              <div
                className={`text-6xl md:text-7xl font-bold tracking-tighter ${stat.color}`}
                style={{ fontFamily: "var(--font-mono, monospace)" }}
              >
                {stat.value}
              </div>
              <div
                className="text-slate-400 font-bold text-lg"
                style={{ fontFamily: "var(--font-heading, sans-serif)" }}
              >
                {stat.label}
              </div>
              <p className="text-slate-500 text-sm">{stat.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
