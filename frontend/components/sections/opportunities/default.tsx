import { Section } from "../../ui/section";

interface OpportunityCard {
  home: string;
  away: string;
  league: string;
  time: string;
  divergence: number;
  confidence: number;
  risk: "faible" | "modéré" | "élevé";
}

interface OpportunitiesProps {
  title?: string;
  description?: string;
  cards?: OpportunityCard[];
  className?: string;
}

const riskColors = {
  faible: { border: "#4ade80", bg: "rgba(34,197,94,0.10)", text: "#4ade80" },
  modéré: { border: "#eab308", bg: "rgba(234,179,8,0.10)", text: "#eab308" },
  élevé: { border: "#f87171", bg: "rgba(248,113,113,0.10)", text: "#f87171" },
};

export default function Opportunities({
  title = "Aperçu des signaux du jour",
  description = "Trois exemples de divergences détectées ce matin. Accède au dashboard pour voir l'ensemble des analyses.",
  cards = [
    {
      home: "PSG",
      away: "Marseille",
      league: "Ligue 1",
      time: "21h00",
      divergence: 11.3,
      confidence: 74,
      risk: "faible",
    },
    {
      home: "Real Madrid",
      away: "Sevilla",
      league: "La Liga",
      time: "20h00",
      divergence: 8.7,
      confidence: 68,
      risk: "modéré",
    },
    {
      home: "Bayern",
      away: "Leverkusen",
      league: "Bundesliga",
      time: "18h30",
      divergence: 7.1,
      confidence: 63,
      risk: "modéré",
    },
  ],
  className,
}: OpportunitiesProps) {
  return (
    <Section className={className}>
      <div className="max-w-container mx-auto flex flex-col items-center gap-10">
        <div className="flex flex-col items-center gap-4 text-center">
          <h2
            className="text-3xl leading-tight font-semibold sm:text-5xl sm:leading-tight"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            {title}
          </h2>
          <p className="text-muted-foreground max-w-[560px] text-lg">
            {description}
          </p>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 w-full">
          {cards.map((card, index) => {
            const colors = riskColors[card.risk];
            return (
              <div
                key={index}
                className="glass-3 rounded-xl p-5 flex flex-col gap-4"
                style={{ borderLeft: `3px solid ${colors.border}` }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div
                      className="text-base font-bold text-foreground"
                      style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                    >
                      {card.home} vs {card.away}
                    </div>
                    <div className="text-muted-foreground text-xs mt-0.5">
                      {card.league} · {card.time}
                    </div>
                  </div>
                  <span
                    className="text-xs px-2 py-0.5 rounded font-medium shrink-0"
                    style={{ background: colors.bg, color: colors.text }}
                  >
                    {card.risk}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className="text-2xl font-semibold font-[family-name:var(--font-mono)]"
                    style={{ color: "#C8F000" }}
                  >
                    +{card.divergence}%
                  </span>
                  <span className="text-muted-foreground text-sm">écart détecté</span>
                </div>
                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Confiance</span>
                    <span className="font-[family-name:var(--font-mono)]">{card.confidence}%</span>
                  </div>
                  <div className="h-0.5 w-full rounded-full bg-border overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${card.confidence}%`,
                        background: "#C8F000",
                      }}
                    />
                  </div>
                </div>
                <a
                  href="/dashboard"
                  className="mt-1 inline-flex items-center justify-center rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
                  style={{
                    background: "rgba(200,240,0,0.10)",
                    color: "#C8F000",
                    border: "1px solid rgba(200,240,0,0.25)",
                  }}
                >
                  Voir l&apos;analyse
                </a>
              </div>
            );
          })}
        </div>
      </div>
    </Section>
  );
}
