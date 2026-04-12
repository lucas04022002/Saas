# Accueil Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Porter le design de référence (`rushplay_accueil_version_transparence`) dans l'archi Next.js existante, section par section, en mettant à jour les composants in-place.

**Architecture:** Mise à jour in-place de chaque composant section existant. Pas de nouveaux fichiers sauf `opportunities/default.tsx` qui devient Signal Preview avec fetch serveur. `CapitalChart` est supprimé (absorbé dans Hero). Ordre final dans `page.tsx` : Navbar → Hero → Stats → SignalPreview → HowItWorks → Pricing → FAQ → Footer.

**Tech Stack:** Next.js 14 App Router, Tailwind CSS v4, shadcn/ui, lucide-react, TypeScript

---

## File Map

| Fichier | Action |
|---|---|
| `frontend/app/globals.css` | Update background + add glass-card/hero-glow/chart-line |
| `frontend/components/sections/navbar/default.tsx` | Logo lime, active link Accueil, backdrop-blur |
| `frontend/components/sections/hero/default.tsx` | Remplacer mockup par SVG chart + métriques |
| `frontend/components/sections/stats/default.tsx` | 3 stats + nouveau layout |
| `frontend/components/sections/opportunities/default.tsx` | Réécriture complète → Signal Preview (Server Component) |
| `frontend/components/sections/items/default.tsx` | Réécriture → Comment ça marche (glass cards) |
| `frontend/components/sections/pricing/default.tsx` | Pro card elevated + lime border + glow |
| `frontend/components/sections/faq/default.tsx` | Styling sombre |
| `frontend/components/sections/footer/default.tsx` | Ajout colonne Compagnie + tagline |
| `frontend/app/page.tsx` | Retirer CapitalChart |

---

## Task 1 : CSS Globals — palette + utilitaires

**Files:**
- Modify: `frontend/app/globals.css`

- [ ] **Étape 1 : Mettre à jour le background et ajouter les variables de surface**

Dans `globals.css`, remplacer dans `:root` et `.dark` :
```css
--background: #10131a;
```
(était `#06090F`)

Puis ajouter dans `:root` et `.dark` ces nouvelles variables (juste après `--shadow-strong`) :
```css
--surface-lowest: #0b0e14;
--surface-low: #16191f;
--surface-container: #1d2027;
--surface-high: #272a31;
--surface-highest: #32353c;
--outline-variant: #454933;
```

- [ ] **Étape 2 : Ajouter les utilitaires CSS dans `styles/utils.css`**

Ajouter à la fin de `frontend/styles/utils.css` :
```css
@utility glass-card {
  background: rgba(49, 53, 60, 0.4);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

@utility hero-glow {
  background: radial-gradient(circle at center, rgba(200, 240, 0, 0.06) 0%, transparent 70%);
}
```

- [ ] **Étape 3 : Ajouter l'animation chart-line dans `globals.css`**

Dans le bloc `@theme inline { ... }`, ajouter :
```css
--animate-chart-line: chart-draw 3s ease-out forwards;

@keyframes chart-draw {
  from { stroke-dashoffset: 1000; }
  to   { stroke-dashoffset: 0; }
}
```

- [ ] **Étape 4 : Vérifier visuellement**

```bash
cd frontend && npm run dev
```
Ouvrir `http://localhost:3000`. Le fond doit être `#10131a` (légèrement plus clair qu'avant).

- [ ] **Étape 5 : Commit**
```bash
git add frontend/app/globals.css frontend/styles/utils.css
git commit -m "feat: update palette + add glass-card/hero-glow/chart-line utilities"
```

---

## Task 2 : Navbar

**Files:**
- Modify: `frontend/components/sections/navbar/default.tsx`

- [ ] **Étape 1 : Réécrire le composant Navbar**

Remplacer tout le contenu de `frontend/components/sections/navbar/default.tsx` par :

```tsx
import { Menu } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";

import { Button } from "../../ui/button";
import { Sheet, SheetContent, SheetTrigger } from "../../ui/sheet";

interface NavbarProps {
  className?: string;
}

export default function Navbar({ className }: NavbarProps) {
  const links = [
    { text: "Accueil", href: "/" },
    { text: "Dashboard", href: "/dashboard" },
    { text: "Historique", href: "/historique" },
    { text: "Tarifs", href: "/#pricing" },
  ];

  return (
    <header
      className={cn(
        "fixed top-0 z-50 w-full bg-[#10131a]/80 backdrop-blur-xl border-b border-[#454933]/20",
        className,
      )}
    >
      <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-6">
        {/* Logo */}
        <Link
          href="/"
          className="text-2xl font-black tracking-tighter text-[#c8f000]"
          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
        >
          RushPlay
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-8">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm font-semibold text-slate-400 hover:text-white transition-colors"
              style={{ fontFamily: "var(--font-heading, sans-serif)" }}
            >
              {link.text}
            </Link>
          ))}
        </nav>

        {/* Actions */}
        <div className="hidden md:flex items-center gap-4">
          <a
            href="/login"
            className="text-sm font-semibold text-slate-400 hover:text-white transition-colors"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Connexion
          </a>
          <a
            href="/signup"
            className="bg-[#c8f000] text-[#2a3400] px-5 py-2 rounded-xl text-sm font-extrabold hover:brightness-110 transition-all"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Commencer
          </a>
        </div>

        {/* Mobile menu */}
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="size-5" />
              <span className="sr-only">Menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="right">
            <nav className="grid gap-6 text-lg font-medium mt-8">
              <Link href="/" className="text-2xl font-black text-[#c8f000]">
                RushPlay
              </Link>
              {links.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className="text-slate-400 hover:text-white transition-colors"
                >
                  {link.text}
                </a>
              ))}
              <a
                href="/signup"
                className="bg-[#c8f000] text-[#2a3400] px-5 py-2 rounded-xl font-extrabold text-center"
              >
                Commencer
              </a>
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}
```

- [ ] **Étape 2 : Vérifier visuellement**

```bash
# dev server déjà lancé
```
Ouvrir `http://localhost:3000`. La navbar doit être fixe, fond sombre blur, logo "RushPlay" en lime, bouton "Commencer" lime.

- [ ] **Étape 3 : Commit**
```bash
git add frontend/components/sections/navbar/default.tsx
git commit -m "feat: redesign navbar — lime logo, backdrop-blur, new CTA"
```

---

## Task 3 : Hero

**Files:**
- Modify: `frontend/components/sections/hero/default.tsx`

- [ ] **Étape 1 : Réécrire le composant Hero**

Remplacer tout le contenu de `frontend/components/sections/hero/default.tsx` par :

```tsx
export default function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-6 overflow-hidden hero-glow pt-16">
      <div className="max-w-4xl text-center z-10">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 bg-[#272a31] px-4 py-1.5 rounded-full mb-8 border border-[#454933]/20">
          <span className="flex h-2 w-2 rounded-full bg-[#c8f000] animate-pulse" />
          <span
            className="text-xs uppercase tracking-widest text-[#c8f000]"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Algorithme V4.2 Live
          </span>
        </div>

        {/* Titre */}
        <h1
          className="text-5xl md:text-8xl font-black tracking-tighter mb-6 leading-[0.9] text-white"
          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
        >
          Les bookmakers se trompent.{" "}
          <br />
          <span className="text-[#c8f000]">RushPlay le voit.</span>
        </h1>

        {/* Description */}
        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          L&apos;intelligence artificielle au service de vos analyses sportives.
          Identifiez les valeurs cachées et battez le marché avec une précision
          mathématique.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <a
            href="/dashboard"
            className="w-full sm:w-auto bg-[#c8f000] text-[#2a3400] px-8 py-4 rounded-xl font-extrabold text-lg transition-transform hover:scale-105 active:scale-95 shadow-[0_20px_40px_rgba(200,240,0,0.2)]"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Accéder aux signaux
          </a>
          <a
            href="/historique"
            className="w-full sm:w-auto bg-[#272a31]/50 border border-[#454933]/20 px-8 py-4 rounded-xl font-bold text-lg hover:bg-[#272a31] transition-colors text-white"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Voir les résultats
          </a>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="relative w-full max-w-6xl mx-auto group">
        <div className="absolute -inset-1 bg-gradient-to-r from-[#c8f000]/20 to-slate-500/20 rounded-xl blur-2xl opacity-30 group-hover:opacity-50 transition-opacity" />
        <div className="relative bg-[#16191f] border border-[#454933]/20 rounded-xl p-8 shadow-2xl overflow-hidden">
          <div className="flex flex-col lg:flex-row gap-12 items-center">
            {/* Chart */}
            <div className="flex-1 w-full">
              <div className="flex items-center justify-between mb-8">
                <h3
                  className="text-2xl font-black text-white"
                  style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                >
                  La transparence comme argument
                </h3>
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <span className="w-3 h-3 rounded-full bg-[#c8f000]" />
                  Profits
                </div>
              </div>
              <div className="relative h-[260px] w-full">
                <svg
                  className="w-full h-full"
                  viewBox="0 0 1000 300"
                  preserveAspectRatio="none"
                >
                  <defs>
                    <linearGradient id="chartGradient" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#c8f000" />
                      <stop offset="100%" stopColor="transparent" />
                    </linearGradient>
                  </defs>
                  <line stroke="#454933" strokeDasharray="5,5" strokeWidth="0.5" x1="0" x2="1000" y1="50" y2="50" />
                  <line stroke="#454933" strokeDasharray="5,5" strokeWidth="0.5" x1="0" x2="1000" y1="150" y2="150" />
                  <line stroke="#454933" strokeDasharray="5,5" strokeWidth="0.5" x1="0" x2="1000" y1="250" y2="250" />
                  <path
                    d="M0,280 L100,260 L200,270 L300,220 L400,190 L500,210 L600,150 L700,120 L800,140 L900,80 L1000,40 V300 H0 Z"
                    fill="url(#chartGradient)"
                    opacity="0.1"
                  />
                  <path
                    className="[stroke-dasharray:1000] [stroke-dashoffset:1000] [animation:chart-draw_3s_ease-out_forwards]"
                    d="M0,280 L100,260 L200,270 L300,220 L400,190 L500,210 L600,150 L700,120 L800,140 L900,80 L1000,40"
                    fill="none"
                    stroke="#c8f000"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="4"
                  />
                </svg>
                <div className="flex justify-between mt-4 text-[10px] text-slate-500 uppercase tracking-widest">
                  <span>Jan 2024</span>
                  <span>Mars 2024</span>
                  <span>Mai 2024</span>
                  <span>Juillet 2024</span>
                  <span>Sept 2024</span>
                </div>
              </div>
            </div>

            {/* Métriques */}
            <div className="lg:w-72 w-full grid grid-cols-2 lg:grid-cols-1 gap-4">
              {[
                { label: "ROI Global", value: "+145.2%", sub: "▲ 12.4% vs mois dernier", highlight: true },
                { label: "Taux de réussite", value: "74.8%", sub: "Moyenne signaux High Conf.", highlight: false },
                { label: "Mise moy. conseillée", value: "2.5%", sub: "Bankroll management", highlight: false },
              ].map((m) => (
                <div
                  key={m.label}
                  className="p-5 rounded-xl bg-[#32353c]/40 border border-[#454933]/15"
                >
                  <div className="text-slate-400 text-xs uppercase mb-1 tracking-wide">
                    {m.label}
                  </div>
                  <div
                    className={`text-2xl font-black ${m.highlight ? "text-[#c8f000]" : "text-white"}`}
                    style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                  >
                    {m.value}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">{m.sub}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Étape 2 : Vérifier visuellement**

Ouvrir `http://localhost:3000`. Le hero doit afficher : badge pulsant, titre géant, 2 CTAs, et le chart SVG avec les 3 métriques à droite.

- [ ] **Étape 3 : Commit**
```bash
git add frontend/components/sections/hero/default.tsx
git commit -m "feat: redesign hero — SVG performance chart remplace mockup"
```

---

## Task 4 : Stats

**Files:**
- Modify: `frontend/components/sections/stats/default.tsx`

- [ ] **Étape 1 : Réécrire le composant Stats**

Remplacer tout le contenu de `frontend/components/sections/stats/default.tsx` par :

```tsx
const STATS = [
  {
    value: "57.6%",
    label: "Précision Moyenne",
    description: "Basé sur les 10 000 derniers signaux générés par l'IA.",
    color: "text-[#c8f000]",
  },
  {
    value: "+12.4%",
    label: "ROI Mensuel Moyen",
    description: "Performance nette après frais de gestion de bankroll.",
    color: "text-slate-300",
  },
  {
    value: "24/7",
    label: "Analyse en Temps Réel",
    description: "Plus de 80 championnats scannés à chaque seconde.",
    color: "text-white",
  },
];

export default function Stats() {
  return (
    <section className="py-24 bg-[#0b0e14]">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 text-center md:text-left">
          {STATS.map((stat) => (
            <div key={stat.label} className="space-y-2">
              <div
                className={`text-6xl md:text-7xl font-bold tracking-tighter ${stat.color}`}
                style={{ fontFamily: "var(--font-mono, monospace)" }}
              >
                {stat.value}
              </div>
              <div
                className="text-slate-400 font-bold text-lg"
                style={{ fontFamily: "var(--font-heading, sans-serif)" }}
              >
                {stat.label}
              </div>
              <p className="text-slate-500 text-sm">{stat.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Étape 2 : Vérifier visuellement**

Ouvrir `http://localhost:3000`. Les 3 stats doivent apparaître sur fond très sombre (`#0b0e14`), chiffres larges.

- [ ] **Étape 3 : Commit**
```bash
git add frontend/components/sections/stats/default.tsx
git commit -m "feat: redesign stats — 3 chiffres clés, fond surface-lowest"
```

---

## Task 5 : Signal Preview (remplace Opportunities)

**Files:**
- Modify: `frontend/components/sections/opportunities/default.tsx`

- [ ] **Étape 1 : Réécrire en Server Component avec fetch**

Remplacer tout le contenu de `frontend/components/sections/opportunities/default.tsx` par :

```tsx
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://saas-oi6c.onrender.com";

interface Opportunity {
  match_id: string;
  home_team: string;
  away_team: string;
  league: string;
  confidence_score: number;
  recommended_bet: string;
  bookmaker_odds: number;
  value_percent: number;
  risk_level: string;
}

async function fetchTopOpportunities(): Promise<Opportunity[]> {
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/v1/opportunities/top?limit=3`,
      { next: { revalidate: 3600 } },
    );
    if (!res.ok) return [];
    const json = await res.json();
    return json.data ?? [];
  } catch {
    return [];
  }
}

function riskColor(risk: string) {
  if (risk === "faible") return { bg: "rgba(34,197,94,0.12)", text: "#4ade80" };
  if (risk === "élevé") return { bg: "rgba(239,68,68,0.12)", text: "#f87171" };
  return { bg: "rgba(234,179,8,0.12)", text: "#eab308" };
}

function SignalCard({ opp }: { opp: Opportunity }) {
  const risk = riskColor(opp.risk_level);
  return (
    <div className="glass-card rounded-xl border border-[#454933]/20 p-6 hover:border-[#c8f000]/30 transition-all group">
      <div className="flex justify-between items-start mb-6">
        <span className="px-3 py-1 bg-[#c8f000]/10 text-[#c8f000] text-[10px] font-bold uppercase tracking-widest rounded-full">
          Haute Confiance
        </span>
        <span
          className="text-xs px-2 py-0.5 rounded font-semibold"
          style={{ background: risk.bg, color: risk.text }}
        >
          {opp.risk_level}
        </span>
      </div>
      <div className="flex items-center justify-between mb-6">
        <div className="text-center flex-1">
          <div className="text-sm font-bold text-white truncate">{opp.home_team}</div>
          <div className="text-xs text-slate-500 mt-0.5">{opp.league}</div>
        </div>
        <div className="flex flex-col items-center px-4">
          <div className="text-xs text-slate-500 mb-1">
            Cote : <span className="text-white font-bold">{opp.bookmaker_odds.toFixed(2)}</span>
          </div>
          <div className="h-px w-16 bg-gradient-to-r from-transparent via-[#454933]/50 to-transparent" />
          <div className="text-[10px] text-[#c8f000] mt-1 font-bold">
            Value : +{opp.value_percent.toFixed(1)}%
          </div>
        </div>
        <div className="text-center flex-1">
          <div className="text-sm font-bold text-white truncate">{opp.away_team}</div>
          <div className="text-xs text-slate-500 mt-0.5">Extérieur</div>
        </div>
      </div>
      <div className="space-y-2 mb-6">
        <div className="flex justify-between text-sm">
          <span className="text-slate-400">Marché</span>
          <span className="text-white font-bold">{opp.recommended_bet}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-400">Probabilité IA</span>
          <span className="text-[#c8f000] font-bold">
            {(opp.confidence_score * 100).toFixed(1)}%
          </span>
        </div>
      </div>
      <a
        href="/dashboard"
        className="block w-full py-3 rounded-lg bg-[#32353c] text-slate-300 font-bold text-sm text-center group-hover:bg-[#c8f000] group-hover:text-[#2a3400] transition-all"
        style={{ fontFamily: "var(--font-heading, sans-serif)" }}
      >
        Voir le signal
      </a>
    </div>
  );
}

function LockedCard() {
  return (
    <div className="glass-card rounded-xl border border-[#454933]/20 p-6 relative overflow-hidden">
      <div className="absolute inset-0 bg-[#32353c]/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center p-6 text-center">
        <div className="text-4xl mb-4">🔒</div>
        <h4
          className="text-white font-bold mb-2"
          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
        >
          Signal Pro Exclusive
        </h4>
        <p className="text-slate-400 text-xs mb-6">
          Ce signal est réservé aux membres de l&apos;abonnement Pro.
        </p>
        <a
          href="/signup?plan=pro"
          className="px-6 py-2 bg-[#c8f000] text-[#2a3400] rounded-lg font-extrabold text-sm hover:brightness-110 transition-all"
          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
        >
          Passer à RushPlay Pro
        </a>
      </div>
      {/* Fond flou derrière */}
      <div className="opacity-20 pointer-events-none">
        <div className="h-6 bg-[#32353c] rounded-full w-2/3 mb-8" />
        <div className="h-24 bg-[#32353c] rounded-lg mb-6" />
        <div className="space-y-3">
          <div className="h-4 bg-[#32353c] rounded-full w-full" />
          <div className="h-4 bg-[#32353c] rounded-full w-1/2" />
        </div>
      </div>
    </div>
  );
}

export default async function Opportunities() {
  const opps = await fetchTopOpportunities();
  const visible = opps.slice(0, 2);

  return (
    <section className="py-24 px-6 bg-[#10131a]">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
          <div>
            <h2
              className="text-4xl md:text-5xl font-black text-white mb-4"
              style={{ fontFamily: "var(--font-heading, sans-serif)" }}
            >
              Signaux du jour
            </h2>
            <p className="text-slate-400 text-lg">
              Aperçu en temps réel des opportunités détectées.
            </p>
          </div>
          <div className="flex gap-2">
            {["Foot", "Tennis", "NBA"].map((sport) => (
              <span
                key={sport}
                className="px-4 py-2 bg-[#272a31] rounded-lg text-xs font-bold uppercase text-slate-400 border border-[#454933]/15"
              >
                {sport}
              </span>
            ))}
          </div>
        </div>

        {/* Cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {visible.map((opp) => (
            <SignalCard key={opp.match_id} opp={opp} />
          ))}
          {/* Pad avec des skeletons si moins de 2 résultats */}
          {visible.length < 2 &&
            Array.from({ length: 2 - visible.length }).map((_, i) => (
              <div
                key={`skeleton-${i}`}
                className="glass-card rounded-xl border border-[#454933]/20 p-6 animate-pulse"
              >
                <div className="h-5 bg-[#32353c] rounded w-1/2 mb-6" />
                <div className="h-24 bg-[#32353c] rounded-lg mb-6" />
                <div className="space-y-3">
                  <div className="h-4 bg-[#32353c] rounded w-full" />
                  <div className="h-4 bg-[#32353c] rounded w-2/3" />
                </div>
                <div className="h-10 bg-[#32353c] rounded-lg mt-6" />
              </div>
            ))}
          <LockedCard />
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Étape 2 : Vérifier visuellement**

Ouvrir `http://localhost:3000`. La section "Signaux du jour" doit afficher 2 vraies cards (ou skeletons si le backend dort) + 1 card verrouillée.

- [ ] **Étape 3 : Commit**
```bash
git add frontend/components/sections/opportunities/default.tsx
git commit -m "feat: Signal Preview — fetch top opportunities, glass cards, locked CTA"
```

---

## Task 6 : Comment ça marche (remplace Items)

**Files:**
- Modify: `frontend/components/sections/items/default.tsx`

- [ ] **Étape 1 : Réécrire le composant**

Remplacer tout le contenu de `frontend/components/sections/items/default.tsx` par :

```tsx
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
```

- [ ] **Étape 2 : Vérifier visuellement**

Ouvrir `http://localhost:3000`. 3 blocs "Comment ça marche" sur fond `#16191f`.

- [ ] **Étape 3 : Commit**
```bash
git add frontend/components/sections/items/default.tsx
git commit -m "feat: redesign 'Comment ça marche' — glass blocks, icons, dark bg"
```

---

## Task 7 : Pricing

**Files:**
- Modify: `frontend/components/sections/pricing/default.tsx`

- [ ] **Étape 1 : Réécrire le composant Pricing**

Remplacer tout le contenu de `frontend/components/sections/pricing/default.tsx` par :

```tsx
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
                      className={`text-base ${
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
```

- [ ] **Étape 2 : Vérifier visuellement**

Ouvrir `http://localhost:3000#pricing`. Plan Pro avec bordure lime, badge "Recommandé", légèrement surélevé. Plan Starter avec bordure grise.

- [ ] **Étape 3 : Commit**
```bash
git add frontend/components/sections/pricing/default.tsx
git commit -m "feat: redesign pricing — Pro elevated, lime border + glow, Recommandé badge"
```

---

## Task 8 : FAQ

**Files:**
- Modify: `frontend/components/sections/faq/default.tsx`

- [ ] **Étape 1 : Mettre à jour le styling de la FAQ**

Remplacer le `return (...)` de `frontend/components/sections/faq/default.tsx` (garder les données existantes, juste changer le JSX) :

```tsx
  return (
    <section className="py-24 bg-[#0b0e14]">
      <div className="max-w-3xl mx-auto px-6">
        <h2
          className="text-3xl font-black text-white mb-12 text-center"
          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
        >
          {title}
        </h2>
        {items !== false && items.length > 0 && (
          <Accordion type="single" collapsible className="w-full space-y-4">
            {items.map((item, index) => (
              <AccordionItem
                key={index}
                value={item.value || `item-${index + 1}`}
                className="bg-[#1d2027] rounded-xl border border-[#454933]/15 overflow-hidden px-6"
              >
                <AccordionTrigger
                  className="text-white font-bold hover:text-[#c8f000] hover:no-underline py-5"
                  style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                >
                  {item.question}
                </AccordionTrigger>
                <AccordionContent>{item.answer}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        )}
      </div>
    </section>
  );
```

- [ ] **Étape 2 : Vérifier visuellement**

Questions FAQ sur fond `#0b0e14`, accordion sombre, trigger en blanc → lime au hover.

- [ ] **Étape 3 : Commit**
```bash
git add frontend/components/sections/faq/default.tsx
git commit -m "feat: redesign FAQ — dark accordion, lime hover"
```

---

## Task 9 : Footer

**Files:**
- Modify: `frontend/components/sections/footer/default.tsx`

- [ ] **Étape 1 : Réécrire le Footer avec 4 colonnes**

Remplacer tout le contenu de `frontend/components/sections/footer/default.tsx` par :

```tsx
import { siteConfig } from "@/config/site";

const COLUMNS = [
  {
    title: "Produit",
    links: [
      { text: "Dashboard", href: "/dashboard" },
      { text: "Historique", href: "/historique" },
      { text: "Tarifs", href: "/#pricing" },
    ],
  },
  {
    title: "Compagnie",
    links: [
      { text: "À propos", href: "#" },
      { text: "Contact", href: "#" },
      { text: "Aide", href: "#" },
    ],
  },
  {
    title: "Légal",
    links: [
      { text: "Confidentialité", href: siteConfig.url },
      { text: "Conditions d'utilisation", href: siteConfig.url },
    ],
  },
];

export default function FooterSection() {
  return (
    <footer className="bg-[#0b0e14] w-full border-t border-[#454933]/15">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-7xl mx-auto py-12 px-6">
        {/* Brand column */}
        <div className="space-y-4">
          <div
            className="text-xl font-bold text-[#c8f000]"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            RushPlay
          </div>
          <p className="text-sm text-slate-500 max-w-xs leading-relaxed">
            Le leader de l&apos;analyse algorithmique pour les parieurs
            exigeants.
          </p>
        </div>
        {/* Link columns */}
        {COLUMNS.map((col) => (
          <div key={col.title} className="flex flex-col gap-4">
            <h4
              className="text-white font-bold uppercase text-xs tracking-widest"
              style={{ fontFamily: "var(--font-heading, sans-serif)" }}
            >
              {col.title}
            </h4>
            {col.links.map((link) => (
              <a
                key={link.text}
                href={link.href}
                className="text-slate-500 hover:text-white transition-colors text-sm"
              >
                {link.text}
              </a>
            ))}
          </div>
        ))}
      </div>
      {/* Bottom bar */}
      <div className="max-w-7xl mx-auto px-6 py-6 border-t border-[#454933]/15 flex flex-col md:flex-row justify-between items-center gap-4">
        <p className="text-sm text-slate-500">
          © {new Date().getFullYear()} RushPlay. Tous droits réservés.
        </p>
        <div className="flex gap-6 text-xs text-slate-600">
          <span>Made for winners.</span>
          <span>Version 4.2.0</span>
        </div>
      </div>
    </footer>
  );
}
```

- [ ] **Étape 2 : Vérifier visuellement**

Footer avec 4 colonnes, logo lime, "Made for winners." en bas à droite.

- [ ] **Étape 3 : Commit**
```bash
git add frontend/components/sections/footer/default.tsx
git commit -m "feat: redesign footer — 4 columns, Made for winners tagline"
```

---

## Task 10 : page.tsx — cleanup

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **Étape 1 : Retirer CapitalChart de page.tsx**

Remplacer le contenu de `frontend/app/page.tsx` par :

```tsx
import FAQ from "../components/sections/faq/default";
import Footer from "../components/sections/footer/default";
import Hero from "../components/sections/hero/default";
import Items from "../components/sections/items/default";
import Navbar from "../components/sections/navbar/default";
import Opportunities from "../components/sections/opportunities/default";
import Pricing from "../components/sections/pricing/default";
import Stats from "../components/sections/stats/default";

export default function Home() {
  return (
    <main className="bg-[#10131a] text-white min-h-screen w-full">
      <Navbar />
      <Hero />
      <Stats />
      <Opportunities />
      <Items />
      <Pricing />
      <FAQ />
      <Footer />
    </main>
  );
}
```

- [ ] **Étape 2 : Vérifier la page complète**

```bash
# dev server déjà lancé
```
Parcourir `http://localhost:3000` de haut en bas. Vérifier l'enchaînement des sections : Navbar fixe → Hero (chart) → Stats (fond très sombre) → Signaux du jour → Comment ça marche → Pricing → FAQ → Footer.

- [ ] **Étape 3 : Vérifier le build sans erreurs**
```bash
cd frontend && npm run build 2>&1 | tail -20
```
Expected : `✓ Compiled successfully` ou similaire, aucune erreur TypeScript.

- [ ] **Étape 4 : Commit final**
```bash
git add frontend/app/page.tsx
git commit -m "feat: page.tsx cleanup — retrait CapitalChart, ordre final des sections"
```
