import { type VariantProps } from "class-variance-authority";
import { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { Badge } from "../../ui/badge";
import { Button, buttonVariants } from "../../ui/button";
import Glow from "../../ui/glow";
import { Mockup, MockupFrame } from "../../ui/mockup";
import Screenshot from "../../ui/screenshot";
import { Section } from "../../ui/section";

interface HeroButtonProps {
  href: string;
  text: string;
  variant?: VariantProps<typeof buttonVariants>["variant"];
  icon?: ReactNode;
  iconRight?: ReactNode;
}

interface HeroProps {
  title?: string;
  description?: string;
  mockup?: ReactNode | false;
  badge?: ReactNode | false;
  buttons?: HeroButtonProps[] | false;
  className?: string;
}

function _DashboardPlaceholder() {
  return (
    <div className="w-full rounded-xl bg-[#0A1220] p-6 min-h-[340px] flex flex-col gap-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex gap-2 items-center">
          <div className="w-3 h-3 rounded-full bg-red-500/60" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
          <div className="w-3 h-3 rounded-full bg-green-500/60" />
        </div>
        <div className="text-xs text-[#7A8FA8] font-[family-name:var(--font-mono)]">
          RushPlay · signaux du jour
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Précision", value: "57.6%", color: "#C8F000" },
          { label: "Signaux actifs", value: "6", color: "#C8F000" },
          { label: "Écart moyen", value: "+11.3%", color: "#C8F000" },
        ].map((kpi) => (
          <div key={kpi.label} className="rounded-lg bg-[#0E1828] border border-[#1E2D42] p-3">
            <div className="text-[#7A8FA8] text-xs mb-1">{kpi.label}</div>
            <div
              className="text-xl font-semibold font-[family-name:var(--font-mono)]"
              style={{ color: kpi.color }}
            >
              {kpi.value}
            </div>
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-2 mt-2">
        {[
          { match: "PSG vs Marseille", league: "Ligue 1", ecart: "+11.3%", conf: 74, risk: "faible" },
          { match: "Real Madrid vs Sevilla", league: "La Liga", ecart: "+8.7%", conf: 68, risk: "modéré" },
          { match: "Bayern vs Leverkusen", league: "Bundesliga", ecart: "+7.1%", conf: 63, risk: "modéré" },
        ].map((m) => (
          <div
            key={m.match}
            className="flex items-center justify-between rounded-lg bg-[#0E1828] border border-[#1E2D42] px-4 py-3"
          >
            <div>
              <div className="text-sm font-semibold text-[#DDD5C4] font-[family-name:var(--font-heading)]">
                {m.match}
              </div>
              <div className="text-xs text-[#7A8FA8]">{m.league}</div>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-[family-name:var(--font-mono)] text-sm font-semibold" style={{ color: "#C8F000" }}>
                {m.ecart}
              </span>
              <span
                className="text-xs px-2 py-0.5 rounded"
                style={{
                  background: m.risk === "faible" ? "rgba(34,197,94,0.12)" : "rgba(234,179,8,0.12)",
                  color: m.risk === "faible" ? "#4ade80" : "#eab308",
                }}
              >
                {m.risk}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Hero({
  title = "Les bookmakers se trompent. RushPlay le voit.",
  description = "Détection algorithmique des écarts entre probabilités réelles et cotes bookmakers — 6 ligues, mis à jour chaque matin.",
  mockup = (
    <Screenshot
      srcLight="/dashboard-light.png"
      srcDark="/dashboard-dark.png"
      alt="RushPlay dashboard"
      width={1248}
      height={765}
      className="w-full"
    />
  ),
  badge = (
    <Badge variant="outline" className="animate-appear">
      <span className="text-muted-foreground">Radar d&apos;opportunités football</span>
    </Badge>
  ),
  buttons = [
    {
      href: "/dashboard",
      text: "Voir les signaux du jour",
      variant: "default",
    },
    {
      href: "/historique",
      text: "Résultats passés",
      variant: "glow",
    },
  ],
  className,
}: HeroProps) {
  return (
    <Section
      className={cn(
        "fade-bottom overflow-hidden pb-0 sm:pb-0 md:pb-0",
        className,
      )}
    >
      <div className="max-w-container mx-auto flex flex-col gap-12 pt-16 sm:gap-24">
        <div className="flex flex-col items-center gap-6 text-center sm:gap-12">
          {badge !== false && badge}
          <h1
            className="animate-appear from-foreground to-foreground dark:to-muted-foreground relative z-10 inline-block bg-linear-to-r bg-clip-text text-4xl leading-tight font-semibold text-balance text-transparent drop-shadow-2xl sm:text-6xl sm:leading-tight md:text-8xl md:leading-tight"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            {title}
          </h1>
          <p className="text-md animate-appear text-muted-foreground relative z-10 max-w-[740px] font-medium text-balance opacity-0 delay-100 sm:text-xl">
            {description}
          </p>
          {buttons !== false && buttons.length > 0 && (
            <div className="animate-appear relative z-10 flex justify-center gap-4 opacity-0 delay-300">
              {buttons.map((button, index) => (
                <Button
                  key={index}
                  variant={button.variant || "default"}
                  size="lg"
                  asChild
                >
                  <a href={button.href}>
                    {button.icon}
                    {button.text}
                    {button.iconRight}
                  </a>
                </Button>
              ))}
            </div>
          )}
          {mockup !== false && (
            <div className="relative w-full pt-12">
              <MockupFrame
                className="animate-appear opacity-0 delay-700"
                size="small"
              >
                <Mockup
                  type="responsive"
                  className="bg-background/90 w-full rounded-xl border-0"
                >
                  {mockup}
                </Mockup>
              </MockupFrame>
              <Glow
                variant="top"
                className="animate-appear-zoom opacity-0 delay-1000"
              />
            </div>
          )}
        </div>
      </div>
    </Section>
  );
}
