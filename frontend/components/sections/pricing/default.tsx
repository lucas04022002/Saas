const PLANS = [
  {
    name: "Starter",
    price: "0€",
    period: "/mois",
    cta: { label: "Commencer gratuitement", href: "/signup" },
    features: [
      { text: "3 signaux gratuits par jour", included: true },
      { text: "Score de confiance", included: true },
      { text: "Aperçu dashboard", included: true },
      { text: "Alertes temps réel illimitées", included: false },
    ],
    highlighted: false,
  },
  {
    name: "Pro",
    price: "10€",
    period: "/mois",
    cta: { label: "Devenir Pro", href: "/signup?plan=pro" },
    features: [
      { text: "Signaux illimités 24/7", included: true },
      { text: "Analyses détaillées", included: true },
      { text: "Explications complètes", included: true },
      { text: "Historique complet", included: true },
      { text: "Filtres avancés", included: true },
    ],
    highlighted: true,
  },
];

export default function Pricing() {
  return (
    <section className="py-24 px-6 bg-[#10131a]" id="pricing">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2
            className="text-4xl md:text-5xl font-black text-white mb-6"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Prêt à battre le marché ?
          </h2>
          <p className="text-slate-400">
            Choisissez le plan qui correspond à votre ambition.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto items-center">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-2xl p-10 flex flex-col ${
                plan.highlighted
                  ? "bg-[#272a31] border-2 border-[#c8f000] shadow-[0_30px_60px_rgba(0,0,0,0.5)] md:-translate-y-4 relative"
                  : "bg-[#1d2027] border border-[#454933]/20"
              }`}
            >
              {plan.highlighted && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-[#c8f000] text-[#2a3400] text-[10px] font-black uppercase tracking-widest px-4 py-1.5 rounded-full">
                  Recommandé
                </div>
              )}
              <div className="mb-8">
                <h3
                  className="text-xl font-bold text-white mb-2"
                  style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                >
                  {plan.name}
                </h3>
                <div className="flex items-baseline gap-1">
                  <span
                    className="text-4xl font-black text-white"
                    style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                  >
                    {plan.price}
                  </span>
                  <span className="text-slate-500 text-sm">{plan.period}</span>
                </div>
              </div>
              <ul className="space-y-4 mb-10 flex-grow">
                {plan.features.map((f) => (
                  <li
                    key={f.text}
                    className={`flex items-center gap-3 text-sm ${
                      f.included ? "text-slate-200" : "text-slate-600"
                    }`}
                  >
                    <span
                      className={`text-base font-bold ${
                        f.included ? "text-[#c8f000]" : "text-slate-700"
                      }`}
                    >
                      {f.included ? "✓" : "✗"}
                    </span>
                    {f.text}
                  </li>
                ))}
              </ul>
              <a
                href={plan.cta.href}
                className={`block w-full py-4 rounded-xl text-center font-extrabold text-lg transition-all ${
                  plan.highlighted
                    ? "bg-[#c8f000] text-[#2a3400] shadow-[0_10px_30px_rgba(200,240,0,0.3)] hover:brightness-110"
                    : "border border-[#454933] text-slate-300 hover:bg-[#272a31]"
                }`}
                style={{ fontFamily: "var(--font-heading, sans-serif)" }}
              >
                {plan.cta.label}
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
