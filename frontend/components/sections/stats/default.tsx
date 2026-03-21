import { Section } from "../../ui/section";

interface StatItemProps {
  label?: string;
  value: string | number;
  suffix?: string;
  description?: string;
}

interface StatsProps {
  items?: StatItemProps[] | false;
  className?: string;
}

export default function Stats({
  items = [
    {
      value: "57.6",
      suffix: "%",
      description: "Précision algorithme",
    },
    {
      value: "+11.3",
      suffix: "%",
      description: "Écart moyen détecté",
    },
    {
      value: "6",
      description: "Ligues analysées",
    },
    {
      value: "24h",
      description: "Mise à jour quotidienne",
    },
  ],
  className,
}: StatsProps) {
  return (
    <Section className={className}>
      <div className="container mx-auto max-w-[960px]">
        {items !== false && items.length > 0 && (
          <div className="grid grid-cols-2 gap-12 sm:grid-cols-4">
            {items.map((item, index) => (
              <div
                key={index}
                className="flex flex-col items-start gap-3 text-left"
              >
                <div className="flex items-baseline gap-1">
                  <div
                    className="from-foreground to-foreground dark:to-brand bg-linear-to-r bg-clip-text text-4xl font-medium text-transparent drop-shadow-[2px_1px_24px_var(--brand-foreground)] transition-all duration-300 sm:text-5xl md:text-6xl font-[family-name:var(--font-mono)]"
                  >
                    {item.value}
                  </div>
                  {item.suffix && (
                    <div className="text-brand text-2xl font-semibold font-[family-name:var(--font-mono)]">
                      {item.suffix}
                    </div>
                  )}
                </div>
                {item.description && (
                  <div className="text-muted-foreground text-sm font-semibold text-pretty">
                    {item.description}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Section>
  );
}
