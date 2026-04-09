import FooterSection from "../../components/sections/footer/default";
import Navbar from "../../components/sections/navbar/default";
import FAQ from "../../components/sections/faq/default";

const PLANS = [
  {
    name: "Starter",
    tag: "Essentiel",
    price: "0€",
    period: "/gratuit",
    cta: { label: "Commencer gratuitement", href: "/signup" },
    highlighted: false,
    features: [
      { text: "3 signaux par jour", included: true },
      { text: "Score de confiance", included: true },
      { text: "Accès Dashboard basique", included: true },
      { text: "Signaux illimités 24/7", included: false },
      { text: "Analyses détaillées", included: false },
      { text: "Historique complet", included: false },
      { text: "Filtres avancés", included: false },
    ],
  },
  {
    name: "Pro",
    tag: "Performance",
    price: "10€",
    period: "/mois",
    cta: { label: "Devenir Pro", href: "/signup?plan=pro" },
    highlighted: true,
    features: [
      { text: "Signaux illimités 24/7", included: true },
      { text: "Score de confiance", included: true },
      { text: "Accès Dashboard complet", included: true },
      { text: "Analyses détaillées", included: true },
      { text: "Historique complet", included: true },
      { text: "Filtres avancés", included: true },
      { text: "Support prioritaire", included: true },
    ],
  },
];

const COMPARISON = [
  { feature: "Signaux quotidiens", starter: "3", pro: "Illimités" },
  { feature: "Score de confiance", starter: "✓", pro: "✓" },
  { feature: "Dashboard", starter: "Basique", pro: "Complet" },
  { feature: "Analyses détaillées", starter: "✗", pro: "✓" },
  { feature: "Historique complet", starter: "✗", pro: "✓" },
  { feature: "Filtres avancés", starter: "✗", pro: "✓" },
  { feature: "Support", starter: "E-mail", pro: "Prioritaire" },
];

export default function TarifsPage() {
  return (
    <div className="min-h-screen bg-[#10131a] text-white">
      <Navbar activePath="/tarifs" />

      <main className="pt-16 overflow-hidden">
        {/* Hero */}
        <section className="max-w-7xl mx-auto px-6 pt-20 pb-16 text-center relative">
          <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-[#c8f000]/5 blur-[120px] rounded-full pointer-events-none" />
          <h1
            className="text-5xl md:text-7xl font-black tracking-tighter mb-6"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Optimisez vos{" "}
            <span className="text-[#c8f000]">Paris</span>
          </h1>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            Accédez à des algorithmes de pointe conçus pour transformer la donnée brute en signaux de victoire. Choisissez le plan qui correspond à votre ambition.
          </p>
        </section>

        {/* Pricing Cards */}
        <section className="max-w-4xl mx-auto px-6 grid grid-cols-1 md:grid-cols-2 gap-8 items-center mb-28">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-2xl p-10 flex flex-col relative ${
                plan.highlighted
                  ? "bg-[#272a31] border-2 border-[#c8f000] shadow-[0_0_50px_rgba(200,240,0,0.15)] md:-translate-y-4"
                  : "bg-[#1d2027] border border-[#454933]/20"
              }`}
            >
              {plan.highlighted && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-[#c8f000] text-[#2a3400] text-[10px] font-black uppercase tracking-widest px-4 py-1.5 rounded-full">
                  Recommandé
                </div>
              )}

              <div className="mb-8">
                <span
                  className={`text-xs uppercase tracking-widest font-bold ${
                    plan.highlighted ? "text-[#c8f000]" : "text-slate-500"
                  }`}
                >
                  {plan.tag}
                </span>
                <h3
                  className={`text-3xl font-black mt-2 ${plan.highlighted ? "text-[#c8f000]" : "text-white"}`}
                  style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                >
                  {plan.name}
                </h3>
                <div className="mt-4 flex items-baseline gap-2">
                  <span
                    className="text-5xl font-black text-white"
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
                      className={`font-black text-base flex-shrink-0 ${
                        f.included ? "text-[#c8f000]" : "text-slate-700"
                      }`}
                    >
                      {f.included ? "✓" : "✗"}
                    </span>
                    <span className={f.included ? "" : "line-through"}>
                      {f.text}
                    </span>
                  </li>
                ))}
              </ul>

              <a
                href={plan.cta.href}
                className={`block w-full py-4 rounded-xl text-center font-extrabold text-sm transition-all ${
                  plan.highlighted
                    ? "bg-[#c8f000] text-[#2a3400] shadow-[0_10px_30px_rgba(200,240,0,0.25)] hover:brightness-110"
                    : "border border-[#454933]/40 text-slate-300 hover:bg-[#272a31]"
                }`}
                style={{ fontFamily: "var(--font-heading, sans-serif)" }}
              >
                {plan.cta.label}
              </a>
            </div>
          ))}
        </section>

        {/* Comparison Table */}
        <section className="max-w-4xl mx-auto px-6 mb-28">
          <h2
            className="text-3xl font-black mb-12 text-center"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Comparaison Détaillée
          </h2>
          <div className="overflow-x-auto rounded-xl bg-[#16191f] border border-[#454933]/15">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-[#272a31]/50 border-b border-[#454933]/15">
                  <th className="p-6 text-sm font-bold text-slate-400">Fonctionnalités</th>
                  <th className="p-6 text-sm font-bold text-center text-white">Starter</th>
                  <th className="p-6 text-sm font-bold text-center text-[#c8f000]">Pro</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#454933]/10">
                {COMPARISON.map((row) => (
                  <tr key={row.feature} className="hover:bg-[#272a31]/20 transition-colors">
                    <td className="p-6 text-sm font-medium text-white">{row.feature}</td>
                    <td
                      className={`p-6 text-center text-sm ${
                        row.starter === "✗" ? "text-slate-600" : "text-slate-400"
                      }`}
                    >
                      {row.starter}
                    </td>
                    <td
                      className={`p-6 text-center text-sm font-bold ${
                        row.pro === "✗" ? "text-slate-600" : "text-[#c8f000]"
                      }`}
                    >
                      {row.pro}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* FAQ */}
        <FAQ title="Questions Fréquentes" />

        {/* CTA */}
        <section className="max-w-7xl mx-auto px-6 py-20">
          <div className="glass-card rounded-3xl p-12 text-center border border-[#454933]/20 relative overflow-hidden">
            <div className="absolute inset-0 bg-[#c8f000]/5 pointer-events-none" />
            <h2
              className="text-4xl font-black mb-6"
              style={{ fontFamily: "var(--font-heading, sans-serif)" }}
            >
              Prêt à dominer le jeu ?
            </h2>
            <p className="text-lg text-slate-400 mb-10 max-w-xl mx-auto">
              Rejoignez les parieurs qui utilisent RushPlay pour sécuriser leurs décisions.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="/signup?plan=pro"
                className="bg-[#c8f000] text-[#2a3400] px-10 py-4 rounded-xl font-extrabold text-lg hover:shadow-[0_0_30px_rgba(200,240,0,0.4)] hover:brightness-110 transition-all"
                style={{ fontFamily: "var(--font-heading, sans-serif)" }}
              >
                Commencer maintenant
              </a>
              <a
                href="/dashboard"
                className="bg-[#272a31] px-10 py-4 rounded-xl font-extrabold text-lg hover:bg-[#32353c] transition-all"
                style={{ fontFamily: "var(--font-heading, sans-serif)" }}
              >
                Voir le Dashboard
              </a>
            </div>
          </div>
        </section>
      </main>

      <FooterSection />
    </div>
  );
}
