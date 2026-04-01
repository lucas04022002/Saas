const STEPS = [
  {
    icon: "🗄️",
    title: "Ingestion de données",
    description:
      "Nous collectons des millions de points de données : statistiques avancées, météo, état de forme, et flux de paris en direct.",
  },
  {
    icon: "🧠",
    title: "Analyse Neuronale",
    description:
      "Notre IA compare les probabilités réelles aux cotes proposées par les bookmakers pour détecter des anomalies de prix.",
  },
  {
    icon: "🔔",
    title: "Signaux Immédiats",
    description:
      "Dès qu'une opportunité est détectée, vous recevez une alerte avec la mise recommandée et le bookmaker optimal.",
  },
];

export default function Items() {
  return (
    <section className="py-24 bg-[#16191f]">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2
            className="text-4xl md:text-5xl font-black text-white mb-6"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Comment ça marche
          </h2>
          <p className="text-slate-400">
            RushPlay n&apos;est pas un bot de pronostics classique. C&apos;est
            un moteur d&apos;ingénierie financière appliqué au sport.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {STEPS.map((step) => (
            <div
              key={step.title}
              className="p-8 bg-[#32353c]/30 rounded-2xl border border-[#454933]/15"
            >
              <div className="w-14 h-14 bg-[#c8f000]/10 rounded-xl flex items-center justify-center mb-6 text-2xl">
                {step.icon}
              </div>
              <h3
                className="text-xl font-bold text-white mb-4"
                style={{ fontFamily: "var(--font-heading, sans-serif)" }}
              >
                {step.title}
              </h3>
              <p className="text-slate-500 leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
