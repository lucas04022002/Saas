import { ReactNode } from "react";

import { siteConfig } from "@/config/site";
import { cn } from "@/lib/utils";

import RushPlayLogo from "../../logos/rushplay";
import {
  Footer,
  FooterBottom,
  FooterColumn,
  FooterContent,
} from "../../ui/footer";

interface FooterLink {
  text: string;
  href: string;
}

interface FooterColumnProps {
  title: string;
  links: FooterLink[];
}

interface FooterProps {
  logo?: ReactNode;
  name?: string;
  columns?: FooterColumnProps[];
  copyright?: string;
  policies?: FooterLink[];
  showModeToggle?: boolean;
  className?: string;
}

export default function FooterSection({
  logo = <RushPlayLogo />,
  name = "RushPlay",
  columns = [
    {
      title: "Produit",
      links: [
        { text: "Dashboard", href: "/dashboard" },
        { text: "Historique", href: "/historique" },
        { text: "Tarifs", href: "#pricing" },
      ],
    },
    {
      title: "Légal",
      links: [
        { text: "Mentions légales", href: siteConfig.url },
        { text: "Confidentialité", href: siteConfig.url },
        { text: "CGU", href: siteConfig.url },
      ],
    },
    {
      title: "Contact",
      links: [
        { text: "Support", href: siteConfig.links.email },
      ],
    },
  ],
  copyright = `© ${new Date().getFullYear()} RushPlay. Tous droits réservés.`,
  policies = [
    { text: "Politique de confidentialité", href: siteConfig.url },
    { text: "Conditions d'utilisation", href: siteConfig.url },
  ],
  className,
}: FooterProps) {
  return (
    <footer className={cn("bg-background w-full px-4", className)}>
      <div className="max-w-container mx-auto">
        <Footer>
          <FooterContent>
            <FooterColumn className="col-span-2 sm:col-span-3 md:col-span-1">
              <div className="flex items-center gap-2">
                {logo}
                <h3 className="text-xl font-bold">{name}</h3>
              </div>
            </FooterColumn>
            {columns.map((column, index) => (
              <FooterColumn key={index}>
                <h3 className="text-md pt-1 font-semibold">{column.title}</h3>
                {column.links.map((link, linkIndex) => (
                  <a
                    key={linkIndex}
                    href={link.href}
                    className="text-muted-foreground text-sm hover:text-foreground transition-colors"
                  >
                    {link.text}
                  </a>
                ))}
              </FooterColumn>
            ))}
          </FooterContent>
          <FooterBottom>
            <div className="flex flex-col gap-2 text-sm text-muted-foreground">
              <p>{copyright}</p>
              <p className="text-xs max-w-[640px]">
                RushPlay est un outil d&apos;analyse statistique du football. Il ne garantit aucun gain.
                Les paris sportifs comportent un risque de perte d&apos;argent. Jouez responsable.
                Aide : 09 74 75 13 13
              </p>
            </div>
            <div className="flex items-center gap-4">
              {policies.map((policy, index) => (
                <a
                  key={index}
                  href={policy.href}
                  className="text-muted-foreground text-xs hover:text-foreground transition-colors"
                >
                  {policy.text}
                </a>
              ))}
            </div>
          </FooterBottom>
        </Footer>
      </div>
    </footer>
  );
}
