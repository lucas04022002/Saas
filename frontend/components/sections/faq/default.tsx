import { ReactNode } from "react";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../../ui/accordion";
import { Section } from "../../ui/section";

interface FAQItemProps {
  question: string;
  answer: ReactNode;
  value?: string;
}

interface FAQProps {
  title?: string;
  items?: FAQItemProps[] | false;
  className?: string;
}

export default function FAQ({
  title = "Questions fréquentes",
  items = [
    {
      question: "Est-ce adapté aux débutants ?",
      answer: (
        <p className="text-muted-foreground mb-4 max-w-[640px] text-balance">
          Oui, RushPlay met en avant les signaux essentiels en premier. L&apos;interface est conçue pour être lisible rapidement, même sans expérience statistique.
        </p>
      ),
    },
    {
      question: "RushPlay garantit-il des résultats ?",
      answer: (
        <p className="text-muted-foreground mb-4 max-w-[640px] text-balance">
          Non. RushPlay est un outil d&apos;analyse statistique. Il détecte des écarts entre probabilités réelles et cotes bookmakers — aucun résultat n&apos;est garanti. Les paris sportifs comportent un risque de perte d&apos;argent.
        </p>
      ),
    },
    {
      question: "Quels championnats sont couverts ?",
      answer: (
        <p className="text-muted-foreground mb-4 max-w-[640px] text-balance">
          Ligue 1, Premier League, La Liga, Bundesliga, Serie A et Ligue des Champions. 6 ligues analysées quotidiennement.
        </p>
      ),
    },
    {
      question: "Comment fonctionne l'algorithme ?",
      answer: (
        <p className="text-muted-foreground mb-4 max-w-[640px] text-balance">
          L&apos;algorithme combine le modèle Elo (force relative des équipes), la distribution de Poisson (estimation des buts) et XGBoost entraîné sur plus de 4 000 matchs historiques. La divergence est calculée entre la probabilité estimée et la cote implicite du bookmaker.
        </p>
      ),
    },
    {
      question: "Quelle différence entre Starter et Pro ?",
      answer: (
        <p className="text-muted-foreground mb-4 max-w-[640px] text-balance">
          Le plan Starter donne accès à 3 signaux par jour avec un aperçu limité. Le Pro débloque tous les signaux, les analyses détaillées, les explications complètes, l&apos;historique et les filtres avancés.
        </p>
      ),
    },
  ],
  className,
}: FAQProps) {
  return (
    <Section className={className}>
      <div className="max-w-container mx-auto flex flex-col items-center gap-8">
        <h2
          className="text-center text-3xl font-semibold sm:text-5xl"
          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
        >
          {title}
        </h2>
        {items !== false && items.length > 0 && (
          <Accordion type="single" collapsible className="w-full max-w-[800px]">
            {items.map((item, index) => (
              <AccordionItem
                key={index}
                value={item.value || `item-${index + 1}`}
              >
                <AccordionTrigger>{item.question}</AccordionTrigger>
                <AccordionContent>{item.answer}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        )}
      </div>
    </Section>
  );
}
