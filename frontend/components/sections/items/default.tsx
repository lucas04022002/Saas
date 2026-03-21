import { EyeIcon, SearchIcon, ZapIcon } from "lucide-react";
import { ReactNode } from "react";

import { Item, ItemDescription, ItemIcon, ItemTitle } from "../../ui/item";
import { Section } from "../../ui/section";

interface ItemProps {
  title: string;
  description: string;
  icon: ReactNode;
}

interface ItemsProps {
  title?: string;
  items?: ItemProps[] | false;
  className?: string;
}

export default function Items({
  title = "Comment ça marche",
  items = [
    {
      title: "L'algorithme analyse les matchs",
      description:
        "Elo, Poisson, XGBoost comparent les probabilités réelles aux cotes bookmakers.",
      icon: <SearchIcon className="size-5 stroke-1" />,
    },
    {
      title: "Les divergences statistiques ressortent",
      description:
        "Seuls les écarts significatifs sont remontés, classés par niveau de confiance.",
      icon: <ZapIcon className="size-5 stroke-1" />,
    },
    {
      title: "Tu lis l'analyse en quelques secondes",
      description:
        "Explication, niveau de risque, éléments à surveiller — tout est lisible avant d'agir.",
      icon: <EyeIcon className="size-5 stroke-1" />,
    },
  ],
  className,
}: ItemsProps) {
  return (
    <Section className={`pb-0 sm:pb-0 md:pb-0 ${className ?? ""}`}>
      <div className="max-w-container mx-auto flex flex-col items-center gap-6 sm:gap-20">
        <h2
          className="max-w-[560px] text-center text-3xl leading-tight font-semibold sm:text-5xl sm:leading-tight"
          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
        >
          {title}
        </h2>
        {items !== false && items.length > 0 && (
          <div className="grid auto-rows-fr grid-cols-1 gap-0 sm:grid-cols-3 sm:gap-4">
            {items.map((item, index) => (
              <Item key={index}>
                <ItemTitle className="flex items-center gap-2">
                  <ItemIcon>{item.icon}</ItemIcon>
                  {item.title}
                </ItemTitle>
                <ItemDescription>{item.description}</ItemDescription>
              </Item>
            ))}
          </div>
        )}
      </div>
    </Section>
  );
}
