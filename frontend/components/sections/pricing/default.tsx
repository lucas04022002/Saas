import { cn } from "@/lib/utils";

import { PricingColumn, PricingColumnProps } from "../../ui/pricing-column";
import { Section } from "../../ui/section";

interface PricingProps {
  title?: string | false;
  description?: string | false;
  plans?: PricingColumnProps[] | false;
  className?: string;
}

export default function Pricing({
  title = "Simple. Transparent. Efficace.",
  description = "Commencez gratuitement, passez Pro quand vous êtes prêt.",
  plans = [
    {
      name: "Starter",
      description: "Pour découvrir RushPlay et comprendre la logique.",
      price: 0,
      priceNote: "Gratuit, sans carte bancaire.",
      cta: {
        variant: "glow",
        label: "Commencer gratuitement",
        href: "/signup",
      },
      features: [
        "3 signaux/jour",
        "Score de confiance",
        "Aperçu dashboard",
        "Analyses limitées",
      ],
      variant: "default",
    },
    {
      name: "Pro",
      description: "Le meilleur ratio vitesse de décision / profondeur.",
      price: 10,
      priceNote: "Par mois. Annulez à tout moment.",
      cta: {
        variant: "default",
        label: "Débloquer toutes les opportunités",
        href: "/signup?plan=pro",
      },
      features: [
        "Tous les signaux",
        "Analyses détaillées",
        "Explications complètes",
        "Historique complet",
        "Filtres avancés",
      ],
      variant: "glow-brand",
    },
  ],
  className = "",
}: PricingProps) {
  return (
    <Section className={cn(className)} id="pricing">
      <div className="mx-auto flex max-w-4xl flex-col items-center gap-12">
        {(title || description) && (
          <div className="flex flex-col items-center gap-4 px-4 text-center sm:gap-8">
            {title && (
              <h2
                className="text-3xl leading-tight font-semibold sm:text-5xl sm:leading-tight"
                style={{ fontFamily: "var(--font-heading, sans-serif)" }}
              >
                {title}
              </h2>
            )}
            {description && (
              <p className="text-md text-muted-foreground max-w-[600px] font-medium sm:text-xl">
                {description}
              </p>
            )}
          </div>
        )}
        {plans !== false && plans.length > 0 && (
          <div className="max-w-container mx-auto grid grid-cols-1 gap-8 sm:grid-cols-2">
            {plans.map((plan) => (
              <PricingColumn
                key={plan.name}
                name={plan.name}
                icon={plan.icon}
                description={plan.description}
                price={plan.price}
                originalPrice={plan.originalPrice}
                promotionText={plan.promotionText}
                priceNote={plan.priceNote}
                cta={plan.cta}
                features={plan.features}
                variant={plan.variant}
                className={plan.className}
              />
            ))}
          </div>
        )}
      </div>
    </Section>
  );
}
