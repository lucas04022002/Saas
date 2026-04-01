export default function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-6 overflow-hidden hero-glow pt-16">
      <div className="max-w-4xl text-center z-10">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 bg-[#272a31] px-4 py-1.5 rounded-full mb-8 border border-[#454933]/20">
          <span className="flex h-2 w-2 rounded-full bg-[#c8f000] animate-pulse" />
          <span
            className="text-xs uppercase tracking-widest text-[#c8f000]"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Algorithme V4.2 Live
          </span>
        </div>

        {/* Titre */}
        <h1
          className="text-5xl md:text-8xl font-black tracking-tighter mb-6 leading-[0.9] text-white"
          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
        >
          Les bookmakers se trompent.{" "}
          <br />
          <span className="text-[#c8f000]">RushPlay le voit.</span>
        </h1>

        {/* Description */}
        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          L&apos;intelligence artificielle au service de vos analyses sportives.
          Identifiez les valeurs cachées et battez le marché avec une précision
          mathématique.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <a
            href="/dashboard"
            className="w-full sm:w-auto bg-[#c8f000] text-[#2a3400] px-8 py-4 rounded-xl font-extrabold text-lg transition-transform hover:scale-105 active:scale-95 shadow-[0_20px_40px_rgba(200,240,0,0.2)]"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Accéder aux signaux
          </a>
          <a
            href="/historique"
            className="w-full sm:w-auto bg-[#272a31]/50 border border-[#454933]/20 px-8 py-4 rounded-xl font-bold text-lg hover:bg-[#272a31] transition-colors text-white"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Voir les résultats
          </a>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="relative w-full max-w-6xl mx-auto group">
        <div className="absolute -inset-1 bg-gradient-to-r from-[#c8f000]/20 to-slate-500/20 rounded-xl blur-2xl opacity-30 group-hover:opacity-50 transition-opacity" />
        <div className="relative bg-[#16191f] border border-[#454933]/20 rounded-xl p-8 shadow-2xl overflow-hidden">
          <div className="flex flex-col lg:flex-row gap-12 items-center">
            {/* Chart */}
            <div className="flex-1 w-full">
              <div className="flex items-center justify-between mb-8">
                <h3
                  className="text-2xl font-black text-white"
                  style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                >
                  La transparence comme argument
                </h3>
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <span className="w-3 h-3 rounded-full bg-[#c8f000]" />
                  Profits
                </div>
              </div>
              <div className="relative h-[260px] w-full">
                <svg
                  className="w-full h-full"
                  viewBox="0 0 1000 300"
                  preserveAspectRatio="none"
                >
                  <defs>
                    <linearGradient id="chartGradient" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#c8f000" />
                      <stop offset="100%" stopColor="transparent" />
                    </linearGradient>
                  </defs>
                  <line stroke="#454933" strokeDasharray="5,5" strokeWidth="0.5" x1="0" x2="1000" y1="50" y2="50" />
                  <line stroke="#454933" strokeDasharray="5,5" strokeWidth="0.5" x1="0" x2="1000" y1="150" y2="150" />
                  <line stroke="#454933" strokeDasharray="5,5" strokeWidth="0.5" x1="0" x2="1000" y1="250" y2="250" />
                  <path
                    d="M0,280 L100,260 L200,270 L300,220 L400,190 L500,210 L600,150 L700,120 L800,140 L900,80 L1000,40 V300 H0 Z"
                    fill="url(#chartGradient)"
                    opacity="0.1"
                  />
                  <path
                    style={{
                      strokeDasharray: 1000,
                      strokeDashoffset: 1000,
                      animation: "chart-draw 3s ease-out forwards",
                    }}
                    d="M0,280 L100,260 L200,270 L300,220 L400,190 L500,210 L600,150 L700,120 L800,140 L900,80 L1000,40"
                    fill="none"
                    stroke="#c8f000"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="4"
                  />
                </svg>
                <div className="flex justify-between mt-4 text-[10px] text-slate-500 uppercase tracking-widest">
                  <span>Jan 2024</span>
                  <span>Mars 2024</span>
                  <span>Mai 2024</span>
                  <span>Juillet 2024</span>
                  <span>Sept 2024</span>
                </div>
              </div>
            </div>

            {/* Métriques */}
            <div className="lg:w-72 w-full grid grid-cols-2 lg:grid-cols-1 gap-4">
              {[
                { label: "ROI Global", value: "+145.2%", sub: "▲ 12.4% vs mois dernier", highlight: true },
                { label: "Taux de réussite", value: "74.8%", sub: "Moyenne signaux High Conf.", highlight: false },
                { label: "Mise moy. conseillée", value: "2.5%", sub: "Bankroll management", highlight: false },
              ].map((m) => (
                <div
                  key={m.label}
                  className="p-5 rounded-xl bg-[#32353c]/40 border border-[#454933]/15"
                >
                  <div className="text-slate-400 text-xs uppercase mb-1 tracking-wide">
                    {m.label}
                  </div>
                  <div
                    className={`text-2xl font-black ${m.highlight ? "text-[#c8f000]" : "text-white"}`}
                    style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                  >
                    {m.value}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">{m.sub}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
