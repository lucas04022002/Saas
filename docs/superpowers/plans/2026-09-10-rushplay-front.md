# RushPlay front — plan d'exécution, partie 1 (socle, composants, pages publiques)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire le front Next.js de RushPlay selon le spec `docs/superpowers/specs/2026-09-10-rushplay-front-design.md` : système visuel noir/blanc/gris, neuf écrans, client API typé, tests Vitest + MSW.

**Architecture:** Next.js 16 (App Router, Turbopack, déjà installé dans `frontend/`), React 19, TypeScript strict, Tailwind v4 avec les jetons du spec en `@theme`. Pages publiques rendues côté serveur (revalidation 60 s), carnet et compte côté client. Un client API unique (`lib/api.ts`) typé par route ; le JWT vit dans un cookie `httpOnly` posé par une route handler `/api/session`. Aucune librairie de composants ; un composant = un fichier.

**Tech Stack:** next 16.1.6, react 19.2, tailwindcss 4.2, typescript 5.9, vitest + @testing-library/react + jsdom, msw 2 pour simuler l'API dans les tests.

## Global Constraints

- Dépôt `C:\Users\lucas\OneDrive\Desktop\Saas--main - Copie`, branche `front-premium` créée depuis `master`. Répertoire de travail : `frontend/`. Node 25, npm 11 (installés).
- Le front ne parle qu'à l'API (`NEXT_PUBLIC_API_URL`, défaut `http://localhost:8000`). Jamais d'accès direct à une base, jamais de calcul métier (probabilités, écarts, mouvements, textes viennent de l'API).
- Enveloppe API : `{"success": bool, "message": str, "data": ...}` ; erreurs `HTTPException` → `{"success": false, "message": "..."}` ; erreurs de validation 422 → `{"detail": [...]}` (format FastAPI).
- Jetons de couleur (exhaustifs) : `--ink #1d1d1f`, `--paper #ffffff`, `--grey #f5f5f7`, `--black #000000`, `--muted #6e6e73`, `--faint #a1a1a6`, `--line rgba(0,0,0,.10)`, `--line-dark rgba(255,255,255,.14)`, `--link #2997ff`. Aucune autre couleur dans le code.
- Polices : `Inter Tight` (titres, chiffres) et `Inter` (texte) via `next/font/google`. Interlettrage négatif sur tout ce qui est en Inter Tight.
- Vocabulaire interdit dans le code et les textes : `prédiction`, `pronostic`, `value bet`, `confiance`, `prediction`, `confidence`. Vocabulaire attendu : favori, probabilité, écart, mouvement, relevé, référence.
- Pas de cartes ni de boîtes : listes = lignes séparées par des filets `1px` ; sections pleine largeur.
- Bandeau ANJ (texte de `GET /api/v1/legal`) dans le pied de page de **chaque** page.
- Tests : `npm test` (Vitest) vert et `npm run build` sans erreur ni avertissement avant chaque commit. Commits en français, préfixes `feat:`, `fix:`, `refactor:`, `test:`, `chore:`.

---

## Structure des fichiers (frontend/)

```
app/
  layout.tsx                 racine : polices, Nav, Footer, jetons
  globals.css                @import tailwind + jetons @theme + base
  page.tsx                   accueil
  matchs/page.tsx            liste
  matchs/[id]/page.tsx       match
  bookmakers/page.tsx        comparateur (Pro)
  carnet/page.tsx            carnet (client)
  track-record/page.tsx      track record
  tarifs/page.tsx            tarifs
  connexion/page.tsx  inscription/page.tsx  compte/page.tsx
  mentions-legales/page.tsx  cgu/page.tsx
  api/session/route.ts       POST (pose le cookie), DELETE (supprime)
components/
  Nav.tsx Footer.tsx BigNumber.tsx Bars.tsx MatchRow.tsx Reserved.tsx
  MovementChart.tsx BookTable.tsx Kpi.tsx BetForm.tsx Reveal.tsx
lib/
  api.ts (client typé) types.ts (types des réponses) session.ts (cookie côté serveur) format.ts (nombres, dates FR)
tests/
  setup.ts msw/handlers.ts msw/server.ts + *.test.tsx
public/photos/stade-nuit.webp stade-jour.webp (+ -900)
vitest.config.ts
```

---

### Task 1 : Branche, remise à zéro du front, jetons, polices, client API, outillage de test

**Files:**
- Delete: `app/dashboard`, `app/historique`, `app/login`, `app/profil`, `app/register`, `app/signal`, `app/tarifs`, `app/page.tsx`, `components/*`, `config/`, `data/`, `lib/auth.ts`, `lib/api.ts` (ancien), `styles/`, `proxy.ts`, `components.json`
- Modify: `package.json`, `app/globals.css`, `app/layout.tsx`, `eslint.config.mjs` (si référence à des dossiers supprimés)
- Create: `lib/types.ts`, `lib/api.ts`, `lib/format.ts`, `vitest.config.ts`, `tests/setup.ts`, `tests/msw/handlers.ts`, `tests/msw/server.ts`, `tests/api.test.ts`, `.env.example`

**Interfaces:**
- Produces: `api` (objet) avec `api.legal()`, `api.matches(params)`, `api.match(id)`, `api.books()`, `api.trackRecord(competition?)`, `api.login()`, `api.signup()`, `api.me()`, `api.bankroll.*` — tous renvoient `data` typé ou lèvent `ApiError(status, message)` ; `formatPct(0.58) → "58 %"`, `formatOdds(1.78) → "1,78"`, `formatSigned(3.1, " pts") → "+3,1 pts"`, `formatDateFr(iso) → "dimanche 14 septembre, 17:15"`, `sinceHours(iso, now) → 9`.

- [ ] **Step 1 : branche et nettoyage**

```bash
cd "C:/Users/lucas/OneDrive/Desktop/Saas--main - Copie" && git checkout -b front-premium && cd frontend && git rm -rq app/dashboard app/historique app/login app/profil app/register app/signal app/tarifs components config data styles && git rm -q app/page.tsx lib/auth.ts lib/api.ts proxy.ts components.json && ls app lib
```

Attendu : `app/` ne contient plus que `globals.css` et `layout.tsx` ; `lib/` ne contient plus que `fonts.ts` et `utils.ts`. Supprimer aussi `lib/fonts.ts` et `lib/utils.ts` (`git rm -q lib/fonts.ts lib/utils.ts`) : les polices sont redéfinies dans `layout.tsx` et `utils.ts` (clsx/tailwind-merge) n'est plus nécessaire.

- [ ] **Step 2 : `package.json` — dépendances**

Remplacer `dependencies` et `devDependencies` par :

```json
"dependencies": {
  "next": "16.1.6",
  "react": "19.2.4",
  "react-dom": "19.2.4"
},
"devDependencies": {
  "@tailwindcss/postcss": "^4.2.1",
  "@testing-library/jest-dom": "^6.6.3",
  "@testing-library/react": "^16.3.0",
  "@types/node": "^20.19.37",
  "@types/react": "19.2.14",
  "@types/react-dom": "19.2.3",
  "@vitejs/plugin-react": "^4.5.0",
  "eslint": "^9.39.4",
  "eslint-config-next": "16.1.6",
  "jsdom": "^26.1.0",
  "msw": "^2.7.0",
  "postcss": "^8.5.8",
  "prettier": "^3.8.1",
  "tailwindcss": "^4.2.1",
  "typescript": "^5.9.3",
  "vitest": "^3.2.0"
}
```

et `scripts` :

```json
"scripts": {
  "dev": "next dev --turbopack",
  "build": "next build",
  "start": "next start",
  "lint": "eslint .",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

Puis `npm install` (attendu : sans erreur ; si une version exacte n'existe pas, prendre la plus proche publiée et le noter dans le rapport).

- [ ] **Step 3 : `app/globals.css` — jetons et base (remplacer intégralement)**

```css
@import "tailwindcss";

@theme {
  --color-ink: #1d1d1f;
  --color-paper: #ffffff;
  --color-grey: #f5f5f7;
  --color-black: #000000;
  --color-muted: #6e6e73;
  --color-faint: #a1a1a6;
  --color-line: rgba(0, 0, 0, 0.1);
  --color-line-dark: rgba(255, 255, 255, 0.14);
  --color-link: #2997ff;
  --font-sans: var(--font-inter), system-ui, sans-serif;
  --font-tight: var(--font-inter-tight), var(--font-inter), system-ui, sans-serif;
  --container-site: 1180px;
}

@layer base {
  html { -webkit-font-smoothing: antialiased; }
  body { @apply bg-paper text-ink font-sans; }
  h1, h2, h3, .display { @apply font-tight; }
  a { color: inherit; }
  :focus-visible { outline: 2px solid var(--color-link); outline-offset: 3px; }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
  }
}

@utility site { @apply mx-auto w-full max-w-site px-5 md:px-12; }
@utility hair { border-top: 1px solid var(--color-line); }
@utility hair-dark { border-top: 1px solid var(--color-line-dark); }
@utility num-hero { @apply font-tight font-extrabold leading-[0.86] tracking-[-0.075em] text-[140px] md:text-[236px]; }
@utility num-page { @apply font-tight font-extrabold leading-[0.85] tracking-[-0.075em] text-[120px] md:text-[180px]; }
@utility num-row { @apply font-tight font-extrabold leading-[0.9] tracking-[-0.06em] text-[44px] md:text-[64px]; }
@utility h-section { @apply font-tight font-extrabold leading-none tracking-[-0.05em] text-[40px] md:text-[56px]; }
@utility h-teams { @apply font-tight font-bold leading-none tracking-[-0.035em] text-[22px] md:text-[30px]; }
@utility h-sub { @apply font-tight font-bold tracking-[-0.035em] text-[24px] md:text-[30px]; }
@utility link { @apply text-link font-medium; }
@utility btn { @apply inline-block rounded-full bg-ink px-6 py-3 text-[15px] font-semibold text-paper; }
@utility btn-ghost { @apply inline-block rounded-full border border-ink bg-paper px-6 py-3 text-[15px] font-semibold text-ink; }
@utility eyebrow { @apply text-xs font-semibold uppercase tracking-[0.08em] text-muted; }
```

- [ ] **Step 4 : `app/layout.tsx` (remplacer intégralement)**

```tsx
import type { Metadata } from "next";
import { Inter, Inter_Tight } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const interTight = Inter_Tight({ subsets: ["latin"], variable: "--font-inter-tight", display: "swap", weight: ["500", "600", "700", "800", "900"] });

export const metadata: Metadata = {
  title: "RushPlay — On ne prédit rien. On lit le marché.",
  description: "Le favori de chaque match, sa vraie probabilité, et là où les bookmakers se contredisent.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${inter.variable} ${interTight.variable}`}>
      <body className="min-h-screen flex flex-col">
        <Nav />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
```

`Nav` et `Footer` sont créés en Task 2 ; pour que cette tâche soit verte seule, créer des versions minimales :

`components/Nav.tsx` :
```tsx
export function Nav() {
  return (
    <header className="bg-black text-paper">
      <div className="site flex h-[52px] items-center justify-between border-b border-line-dark">
        <a href="/" className="font-tight text-[19px] font-extrabold tracking-[-0.04em]">RushPlay</a>
      </div>
    </header>
  );
}
```

`components/Footer.tsx` :
```tsx
export function Footer() {
  return <footer className="bg-grey text-muted text-xs"><div className="site py-10">RushPlay</div></footer>;
}
```

- [ ] **Step 5 : `lib/types.ts`**

```ts
export type Outcome = "home" | "draw" | "away";
export type Probs = { home: number; draw: number; away: number };
export type Plan = "STARTER" | "PRO" | "ELITE";

export type Favourite = { outcome: Outcome; label: string; prob: number; source: string };
export type BestGap = { bookmaker: string; outcome: Outcome; gap: number; odds: number };

export type MatchSummary = {
  id: string; competition: string; league: string; home_team: string; away_team: string;
  kickoff_at: string; status: "SCHEDULED" | "LIVE" | "FINISHED" | "POSTPONED";
  favourite: Favourite | null; reference: Probs | null; best_gap: BestGap | null;
  movement: Probs | null; odds_taken_at: string | null; locked: boolean;
};

export type Book = { bookmaker: string; label: string; home: number; draw: number; away: number; margin: number; gaps: Probs };
export type Form = { played: number; wins: number; draws: number; losses: number; goals_for: number; goals_against: number; sequence: string };
export type H2H = { kickoff_at: string; home: string; away: string; score: string };

export type MatchDetail = MatchSummary & {
  books: Book[] | null;
  reference_book: { bookmaker: string; label: string; home: number; draw: number; away: number; margin: number } | null;
  history: { taken_at: string; reference: Probs }[] | null;
  form: { home: Form; away: Form }; h2h: H2H[]; analysis: string | null;
  result: { home: number; away: number } | null;
};

export type BookRow = { bookmaker: string; label: string; matches: number; avg_margin: number | null; gaps_above_threshold: number;
  best: { match_id: string; home_team: string; away_team: string; kickoff_at: string; outcome: Outcome; gap: number; odds: number } | null };

export type TrackRow = { competition: string; played: number; favourite_won: number; favourite_rate: number };

export type Bet = { id: string; match_id: string; home_team: string; away_team: string; competition: string; kickoff_at: string;
  outcome: Outcome; bookmaker: string; odds: number; stake: number; status: "PENDING" | "WON" | "LOST" | "VOID"; payout: number | null;
  created_at: string; settled_at: string | null };
export type BankrollSummary = { stakes: number; settled_stakes: number; payouts: number; profit: number; roi: number | null; pending: number; settled: number;
  by_bookmaker: Record<string, { stakes: number; payouts: number; profit: number; bets: number }>;
  by_competition: Record<string, { stakes: number; payouts: number; profit: number; bets: number }> };

export type User = { id: string; first_name: string; email: string; role: string; subscription_plan: Plan };
export type Legal = { warning: string; minimum_age: number; positioning: string };
export type Pagination = { page: number; limit: number; total: number };

export const COMPETITIONS: Record<string, string> = {
  E0: "Premier League", F1: "Ligue 1", SP1: "Liga", D1: "Bundesliga", I1: "Serie A", CL: "Ligue des Champions",
};
export const BOOK_LABELS: Record<string, string> = {
  betclic_fr: "Betclic", winamax_fr: "Winamax", unibet_fr: "Unibet", pmu_fr: "PMU", netbet_fr: "NetBet", pinnacle: "Pinnacle",
};
```

- [ ] **Step 6 : test `tests/api.test.ts` (écrire avant `lib/api.ts`)**

```ts
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { api, ApiError } from "@/lib/api";

const API = "http://localhost:8000";

describe("client API", () => {
  it("déballe data sur succès", async () => {
    server.use(http.get(`${API}/api/v1/legal`, () => HttpResponse.json({ success: true, message: "ok", data: { warning: "W", minimum_age: 18, positioning: "P" } })));
    const legal = await api.legal();
    expect(legal.minimum_age).toBe(18);
  });

  it("lève ApiError avec le message de l'API sur erreur HTTPException", async () => {
    server.use(http.get(`${API}/api/v1/matches/xyz`, () => HttpResponse.json({ success: false, message: "Match not found" }, { status: 404 })));
    await expect(api.match("xyz")).rejects.toMatchObject({ status: 404, message: "Match not found" });
  });

  it("lève ApiError avec le premier message de validation sur 422", async () => {
    server.use(http.post(`${API}/api/v1/auth/signup`, () => HttpResponse.json({ detail: [{ loc: ["body", "birth_date"], msg: "Value error, Vous devez avoir 18 ans ou plus" }] }, { status: 422 })));
    await expect(api.signup({ first_name: "A", email: "a@a.fr", password: "motdepasse123", birth_date: "2015-01-01" })).rejects.toBeInstanceOf(ApiError);
    await expect(api.signup({ first_name: "A", email: "a@a.fr", password: "motdepasse123", birth_date: "2015-01-01" })).rejects.toMatchObject({ message: "Vous devez avoir 18 ans ou plus" });
  });

  it("envoie le jeton en Authorization quand il est fourni", async () => {
    let auth = "";
    server.use(http.get(`${API}/api/v1/bankroll`, ({ request }) => { auth = request.headers.get("authorization") ?? ""; return HttpResponse.json({ success: true, message: "", data: { items: [], summary: {} } }); }));
    await api.bankroll.list("tok");
    expect(auth).toBe("Bearer tok");
  });
});
```

`tests/msw/server.ts` :
```ts
import { setupServer } from "msw/node";
import { handlers } from "./handlers";
export const server = setupServer(...handlers);
```

`tests/msw/handlers.ts` (les gabarits par défaut, complétés dans les tâches suivantes) :
```ts
import { http, HttpResponse } from "msw";
export const API = "http://localhost:8000";
export const legal = { warning: "Les paris sportifs comportent des risques : endettement, dépendance… Appelez le 09 74 75 13 13 (appel non surtaxé).", minimum_age: 18, positioning: "Nous ne prédisons pas. Nous vous montrons ce que le marché pense, et où il se contredit." };
export const handlers = [
  http.get(`${API}/api/v1/legal`, () => HttpResponse.json({ success: true, message: "", data: legal })),
];
```

`tests/setup.ts` :
```ts
import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./msw/server";
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

`vitest.config.ts` :
```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";
export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", setupFiles: ["./tests/setup.ts"], globals: false, css: false, env: { NEXT_PUBLIC_API_URL: "http://localhost:8000" } },
  resolve: { alias: { "@": path.resolve(__dirname, ".") } },
});
```

Run : `npm test` → Expected : échec sur `Cannot find module '@/lib/api'`.

- [ ] **Step 7 : `lib/api.ts`**

```ts
import type { BankrollSummary, Bet, BookRow, Legal, MatchDetail, MatchSummary, Pagination, TrackRow, User } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); this.name = "ApiError"; }
}

type Envelope<T> = { success: boolean; message: string; data: T };

async function call<T>(path: string, init: RequestInit & { token?: string; revalidate?: number } = {}): Promise<T> {
  const { token, revalidate, ...rest } = init;
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(rest.headers as Record<string, string>) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...rest, headers, next: revalidate !== undefined ? { revalidate } : undefined } as RequestInit);
  let body: unknown = null;
  try { body = await res.json(); } catch { body = null; }
  if (!res.ok) {
    const b = body as { message?: string; detail?: unknown };
    let message = b?.message ?? res.statusText;
    if (Array.isArray(b?.detail) && b.detail.length) {
      const msg = String((b.detail[0] as { msg?: string }).msg ?? "");
      message = msg.replace(/^Value error, /, "");
    } else if (typeof b?.detail === "string") message = b.detail;
    throw new ApiError(res.status, message);
  }
  return (body as Envelope<T>).data;
}

const qs = (p: Record<string, string | number | undefined>) =>
  Object.entries(p).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");

export const api = {
  legal: () => call<Legal>("/api/v1/legal", { revalidate: 3600 }),
  matches: (p: { date?: string; competition?: string; page?: number; limit?: number } = {}, token?: string) =>
    call<{ items: MatchSummary[]; pagination: Pagination }>(`/api/v1/matches?${qs(p)}`, { token, revalidate: 60 }),
  match: (id: string, token?: string) => call<MatchDetail>(`/api/v1/matches/${id}`, { token, revalidate: 60 }),
  books: (token?: string) => call<{ items: BookRow[]; threshold: number }>("/api/v1/books", { token, revalidate: 60 }),
  trackRecord: (competition?: string) => call<{ items: TrackRow[]; note: string }>(`/api/v1/track-record?${qs({ competition })}`, { revalidate: 300 }),
  login: (email: string, password: string) => call<{ access_token: string; user: User }>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  signup: (p: { first_name: string; email: string; password: string; birth_date: string }) =>
    call<{ access_token: string; user: User }>("/api/v1/auth/signup", { method: "POST", body: JSON.stringify(p) }),
  me: (token: string) => call<User>("/api/v1/auth/me", { token, cache: "no-store" }),
  bankroll: {
    list: (token: string) => call<{ items: Bet[]; summary: BankrollSummary }>("/api/v1/bankroll", { token, cache: "no-store" }),
    create: (token: string, p: { match_id: string; outcome: string; bookmaker: string; odds: number; stake: number }) =>
      call<Bet>("/api/v1/bankroll", { method: "POST", token, body: JSON.stringify(p) }),
    remove: (token: string, id: string) => call<{ id: string }>(`/api/v1/bankroll/${id}`, { method: "DELETE", token }),
    void: (token: string, id: string) => call<Bet>(`/api/v1/bankroll/${id}/void`, { method: "POST", token }),
  },
};
```

- [ ] **Step 8 : `lib/format.ts` + test `tests/format.test.ts`**

```ts
// lib/format.ts
const nf1 = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const formatPct = (p: number) => `${Math.round(p * 100)} %`;
export const formatPctInt = (p: number) => `${Math.round(p * 100)}`;
export const formatOdds = (o: number) => nf2.format(o);
export const formatMargin = (m: number) => `${nf1.format(m * 100)} %`;
export const formatGap = (g: number) => `${g >= 0 ? "+" : "−"}${nf1.format(Math.abs(g) * 100)} %`;
export const formatSigned = (x: number, unit = "") => `${x >= 0 ? "+" : "−"}${nf1.format(Math.abs(x))}${unit}`;
export const formatEuro = (x: number) => `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(x)} €`;
export const formatDateFr = (iso: string) =>
  new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Paris" }).format(new Date(iso)).replace(" à ", ", ");
export const formatTimeFr = (iso: string) => new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Paris" }).format(new Date(iso));
export const formatDayShort = (iso: string) => new Intl.DateTimeFormat("fr-FR", { weekday: "short", day: "numeric", timeZone: "Europe/Paris" }).format(new Date(iso));
export const sinceHours = (iso: string, now = new Date()) => Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 3600000));
export const parisDate = (d = new Date()) => new Intl.DateTimeFormat("fr-CA", { timeZone: "Europe/Paris" }).format(d); // YYYY-MM-DD
```

```ts
// tests/format.test.ts
import { describe, expect, it } from "vitest";
import { formatDateFr, formatGap, formatOdds, formatPct, formatSigned, sinceHours } from "@/lib/format";
describe("format", () => {
  it("pourcentage arrondi avec espace insécable", () => expect(formatPct(0.5821)).toBe("58 %"));
  it("cote avec virgule", () => expect(formatOdds(1.78)).toBe("1,78"));
  it("écart signé", () => { expect(formatGap(0.032)).toBe("+3,2 %"); expect(formatGap(-0.1)).toBe("−10,0 %"); });
  it("signé avec unité", () => expect(formatSigned(3.1, " pts")).toBe("+3,1 pts"));
  it("date française", () => expect(formatDateFr("2026-09-13T15:15:00Z")).toBe("dimanche 13 septembre, 17:15"));
  it("heures écoulées", () => expect(sinceHours("2026-09-13T03:00:00Z", new Date("2026-09-13T12:00:00Z"))).toBe(9));
});
```

Note : `Intl` en fr-FR insère une espace fine insécable avant `%` et un signe moins typographique ; les tests ci-dessus comparent avec les chaînes que `Intl` produit réellement sur Node 25 (espace insécable U+202F ou U+00A0 selon la version) — si l'égalité stricte échoue à cause du type d'espace, normaliser dans `format.ts` avec `.replace(/\u202f/g, "\u00a0")` et écrire les attendus avec `\u00a0`. Ne pas assouplir les tests avec des regex vagues.

- [ ] **Step 9 : `.env.example`, lancer, committer**

`.env.example` : `NEXT_PUBLIC_API_URL=http://localhost:8000`

Run : `npm test` → tous verts. Run : `npm run build` → sans erreur. Run : `npm run lint` → sans erreur (adapter `eslint.config.mjs` si des règles visent des dossiers supprimés).

```bash
git add -A && git commit -m "chore(front): remise à zéro, jetons du système visuel, polices, client API typé, Vitest + MSW"
```

---

### Task 2 : Composants de base — Nav, Footer, BigNumber, Bars, Reserved, MatchRow, Reveal

**Files:**
- Create/Modify: `components/Nav.tsx`, `components/Footer.tsx`, `components/BigNumber.tsx`, `components/Bars.tsx`, `components/Reserved.tsx`, `components/MatchRow.tsx`, `components/Reveal.tsx`, `lib/session.ts`
- Test: `tests/components.test.tsx`

**Interfaces:**
- `Nav({ user }: { user: User | null })` (serveur : lit la session) ; `Footer()` (serveur : appelle `api.legal()`).
- `BigNumber({ value, suffix, className })` : affiche `value` (entier) avec compte animé de 0 à `value` en 600 ms au premier passage dans l'écran ; sans animation si `prefers-reduced-motion` ou en test (jsdom n'a pas `IntersectionObserver` → afficher la valeur finale immédiatement).
- `Bars({ probs, favourite, dark })` : trois lignes `Lyon — barre — 58` ; la ligne du favori en encre, les autres en `muted`.
- `Reserved({ dark })` : bloc « Réservé aux abonnés › » (lien `/tarifs`).
- `MatchRow({ match })` : ligne de liste (équipes + méta / meilleur écart ou « Réservé » / mouvement / chiffre) ; chiffre en `faint` quand `favourite.prob < 0.45` (« serré »).
- `Reveal({ children })` : fondu à l'entrée (client, `IntersectionObserver`, sans effet si reduced motion).
- `lib/session.ts` : `getToken()` (lit le cookie `rp_token` via `cookies()` de `next/headers`) et `getUser()` (appelle `api.me(token)` ou `null`).

- [ ] **Step 1 : tests (avant le code)**

```tsx
// tests/components.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BigNumber } from "@/components/BigNumber";
import { Bars } from "@/components/Bars";
import { MatchRow } from "@/components/MatchRow";
import { Reserved } from "@/components/Reserved";
import type { MatchSummary } from "@/lib/types";

const base: MatchSummary = {
  id: "m1", competition: "F1", league: "Ligue 1", home_team: "Lyon", away_team: "Marseille", kickoff_at: "2026-09-13T15:15:00Z", status: "SCHEDULED",
  favourite: { outcome: "home", label: "Lyon", prob: 0.58, source: "pinnacle" }, reference: { home: 0.58, draw: 0.24, away: 0.18 },
  best_gap: { bookmaker: "betclic_fr", outcome: "home", gap: 0.032, odds: 1.78 }, movement: { home: 3.1, draw: -1.2, away: -1.9 },
  odds_taken_at: "2026-09-13T10:00:00Z", locked: false,
};

describe("BigNumber", () => {
  it("affiche la valeur finale sans IntersectionObserver", () => {
    render(<BigNumber value={58} suffix="%" />);
    expect(screen.getByText("58")).toBeInTheDocument();
    expect(screen.getByText("%")).toBeInTheDocument();
  });
});

describe("Bars", () => {
  it("trois lignes avec les valeurs en pourcentage entier", () => {
    render(<Bars probs={base.reference!} favourite="home" home="Lyon" away="Marseille" />);
    expect(screen.getByText("58")).toBeInTheDocument();
    expect(screen.getByText("24")).toBeInTheDocument();
    expect(screen.getByText("18")).toBeInTheDocument();
    expect(screen.getByText("Marseille")).toBeInTheDocument();
  });
});

describe("MatchRow", () => {
  it("abonné : écart et mouvement visibles, chiffre et favori", () => {
    render(<MatchRow match={base} />);
    expect(screen.getByText("Lyon – Marseille")).toBeInTheDocument();
    expect(screen.getByText("Betclic +3,2 %")).toBeInTheDocument();
    expect(screen.getByText("▲ 3 pts")).toBeInTheDocument();
    expect(screen.getByText("58")).toBeInTheDocument();
    expect(screen.getByText("Lyon favori")).toBeInTheDocument();
  });
  it("non abonné : « Réservé » à la place de l'écart", () => {
    render(<MatchRow match={{ ...base, locked: true, best_gap: null, movement: null }} />);
    expect(screen.getByText("Réservé")).toBeInTheDocument();
    expect(screen.queryByText(/Betclic/)).not.toBeInTheDocument();
  });
  it("match serré : libellé « serré » et pas de couleur favori", () => {
    render(<MatchRow match={{ ...base, favourite: { outcome: "home", label: "Lens", prob: 0.41, source: "pinnacle" }, reference: { home: 0.41, draw: 0.3, away: 0.29 } }} />);
    expect(screen.getByText("Lens, serré")).toBeInTheDocument();
  });
  it("sans relevé : tiret et « pas encore de relevé »", () => {
    render(<MatchRow match={{ ...base, favourite: null, reference: null, best_gap: null, movement: null, odds_taken_at: null }} />);
    expect(screen.getByText("pas encore de relevé")).toBeInTheDocument();
  });
});

describe("Reserved", () => {
  it("lien vers les tarifs", () => {
    render(<Reserved />);
    expect(screen.getByRole("link", { name: /Réservé aux abonnés/ })).toHaveAttribute("href", "/tarifs");
  });
});
```

Run : `npm test` → échecs `Cannot find module`.

- [ ] **Step 2 : composants**

`components/BigNumber.tsx` :
```tsx
"use client";
import { useEffect, useRef, useState } from "react";

export function BigNumber({ value, suffix, className = "" }: { value: number; suffix?: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const canAnimate = typeof window !== "undefined" && "IntersectionObserver" in window && !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const [shown, setShown] = useState(canAnimate ? 0 : value);
  useEffect(() => {
    if (!canAnimate || !ref.current) return;
    const el = ref.current;
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      const start = performance.now();
      const tick = (t: number) => {
        const k = Math.min(1, (t - start) / 600);
        setShown(Math.round(value * (1 - Math.pow(1 - k, 3))));
        if (k < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, { threshold: 0.4 });
    io.observe(el);
    return () => io.disconnect();
  }, [canAnimate, value]);
  return (
    <span ref={ref} className={className} aria-label={`${value}${suffix ?? ""}`}>
      <span>{shown}</span>{suffix ? <sup className="align-top text-[0.28em] font-bold tracking-[-0.02em] relative top-[0.3em] ml-[0.02em]">{suffix}</sup> : null}
    </span>
  );
}
```

`components/Bars.tsx` :
```tsx
import type { Outcome, Probs } from "@/lib/types";
import { formatPctInt } from "@/lib/format";

export function Bars({ probs, favourite, home, away, dark = false }: { probs: Probs; favourite: Outcome | null; home: string; away: string; dark?: boolean }) {
  const rows: [Outcome, string][] = [["home", home], ["draw", "Nul"], ["away", away]];
  const line = dark ? "border-line-dark" : "border-line";
  const track = dark ? "bg-[#3a3a3c]" : "bg-[#e5e5ea]";
  return (
    <div className={`mt-6 border-b ${line}`}>
      {rows.map(([k, label]) => {
        const fav = k === favourite;
        const color = fav ? (dark ? "text-paper" : "text-ink") : "text-muted";
        const fill = fav ? (dark ? "bg-paper" : "bg-ink") : "bg-faint";
        return (
          <div key={k} className={`grid grid-cols-[90px_1fr_44px] md:grid-cols-[110px_1fr_48px] items-center gap-4 border-t ${line} py-3 text-[15px] font-semibold ${color}`}>
            <span>{label}</span>
            <span className={`relative block h-[2px] ${track}`}><span className={`absolute -top-px left-0 h-1 ${fill}`} style={{ width: `${probs[k] * 100}%` }} /></span>
            <span className="text-right tabular-nums">{formatPctInt(probs[k])}</span>
          </div>
        );
      })}
    </div>
  );
}
```

`components/Reserved.tsx` :
```tsx
export function Reserved({ dark = false, what = "aux abonnés" }: { dark?: boolean; what?: string }) {
  return (
    <a href="/tarifs" className={`block border-t border-b py-6 ${dark ? "border-line-dark text-paper" : "border-line text-ink"}`}>
      <span className="text-[17px] font-semibold">Réservé {what} ›</span>
      <span className={`mt-1 block text-[14px] ${dark ? "text-faint" : "text-muted"}`}>Les écarts entre bookmakers, le mouvement des cotes et le comparateur.</span>
    </a>
  );
}
```

`components/MatchRow.tsx` :
```tsx
import Link from "next/link";
import type { MatchSummary } from "@/lib/types";
import { BOOK_LABELS } from "@/lib/types";
import { formatGap, formatPctInt, formatSigned, formatTimeFr, sinceHours } from "@/lib/format";

export function MatchRow({ match }: { match: MatchSummary }) {
  const fav = match.favourite;
  const tight = !!fav && fav.prob < 0.45;
  const mv = match.movement && fav ? match.movement[fav.outcome] : null;
  const stale = match.odds_taken_at ? sinceHours(match.odds_taken_at) : null;
  const refLabel = fav ? (fav.source === "moyenne" ? "moyenne, Pinnacle absent" : "référence Pinnacle") : "pas encore de relevé";
  return (
    <Link href={`/matchs/${match.id}`} className="grid grid-cols-[1fr_auto] md:grid-cols-[1.6fr_1fr_1fr_auto] items-center gap-3 md:gap-6 border-t border-line py-5 md:py-6 hover:bg-grey/60 transition-colors">
      <div>
        <div className="h-teams">{match.home_team} – {match.away_team}</div>
        <div className="mt-1.5 text-[13.5px] text-muted">{match.league} · {formatTimeFr(match.kickoff_at)} · {refLabel}{stale !== null && stale >= 6 ? ` · relevé il y a ${stale} h` : ""}</div>
      </div>
      <div className="hidden md:block text-[14px] text-muted">
        {match.locked ? <><b className="block text-[15px] font-semibold text-ink">Réservé</b>écarts</> :
          match.best_gap ? <><b className="block text-[15px] font-semibold text-ink">{BOOK_LABELS[match.best_gap.bookmaker] ?? match.best_gap.bookmaker} {formatGap(match.best_gap.gap)}</b>meilleur écart</> :
          <><b className="block text-[15px] font-semibold text-ink">—</b>aucun écart</>}
      </div>
      <div className="hidden md:block text-[14px] text-muted">
        {mv === null ? <><b className="block text-[15px] font-semibold text-ink">—</b>stable</> :
          <><b className="block text-[15px] font-semibold text-ink">{mv >= 0 ? "▲" : "▼"} {formatSigned(mv, " pts").replace(/^[+−]/, "")}</b>depuis le premier relevé</>}
      </div>
      <div className={`num-row text-right min-w-[110px] md:min-w-[150px] ${tight || !fav ? "text-faint" : "text-ink"}`}>
        {fav ? formatPctInt(fav.prob) : "—"}
        <small className="mt-1.5 block font-sans text-[12px] font-medium tracking-normal text-muted">{fav ? (tight ? `${fav.label}, serré` : `${fav.label} favori`) : "pas encore de relevé"}</small>
      </div>
    </Link>
  );
}
```

Attention au test « ▲ 3 pts » : le mouvement 3,1 doit s'afficher « ▲ 3 pts » (arrondi à l'entier dans la liste). Remplacer dans `MatchRow` l'expression du mouvement par `` `${mv >= 0 ? "▲" : "▼"} ${Math.round(Math.abs(mv))} pts` `` et ne pas utiliser `formatSigned` ici.

`components/Reveal.tsx` :
```tsx
"use client";
import { useEffect, useRef, useState } from "react";
export function Reveal({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [on, setOn] = useState(false);
  useEffect(() => {
    if (!ref.current || !("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setOn(true); return; }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setOn(true); io.disconnect(); } }, { threshold: 0.15 });
    io.observe(ref.current);
    return () => io.disconnect();
  }, []);
  return <div ref={ref} className={`${className} transition-opacity duration-700 ${on ? "opacity-100" : "opacity-0"}`}>{children}</div>;
}
```

`lib/session.ts` :
```ts
import { cookies } from "next/headers";
import { api, ApiError } from "./api";
import type { User } from "./types";
export const TOKEN_COOKIE = "rp_token";
export async function getToken(): Promise<string | undefined> { return (await cookies()).get(TOKEN_COOKIE)?.value; }
export async function getUser(): Promise<User | null> {
  const token = await getToken();
  if (!token) return null;
  try { return await api.me(token); } catch (e) { if (e instanceof ApiError) return null; throw e; }
}
export const isPro = (u: User | null) => !!u && (u.subscription_plan === "PRO" || u.subscription_plan === "ELITE");
```

`components/Nav.tsx` (serveur) :
```tsx
import Link from "next/link";
import { getUser } from "@/lib/session";
export async function Nav() {
  const user = await getUser();
  const links = [["/matchs", "Matchs"], ["/bookmakers", "Bookmakers"], ["/track-record", "Track record"], ["/tarifs", "Tarifs"]];
  return (
    <header className="bg-black text-paper sticky top-0 z-20">
      <div className="site flex h-[52px] items-center justify-between border-b border-line-dark">
        <Link href="/" className="font-tight text-[19px] font-extrabold tracking-[-0.04em]">RushPlay</Link>
        <nav className="flex items-center gap-5 md:gap-8 text-[12.5px] font-medium text-[#c7c7cc]">
          {links.map(([href, label]) => <Link key={href} href={href} className="hover:text-paper">{label}</Link>)}
          {user ? <Link href={user.subscription_plan === "STARTER" ? "/compte" : "/carnet"} className="text-paper">{user.first_name}</Link> : <Link href="/connexion" className="text-paper">Se connecter</Link>}
        </nav>
      </div>
    </header>
  );
}
```

`components/Footer.tsx` (serveur) :
```tsx
import Link from "next/link";
import { api } from "@/lib/api";
export async function Footer() {
  let warning = "Les paris sportifs comportent des risques : endettement, dépendance… Appelez le 09 74 75 13 13 (appel non surtaxé).";
  try { warning = (await api.legal()).warning; } catch { /* API indisponible : texte de secours */ }
  const links = [["/matchs", "Matchs"], ["/bookmakers", "Bookmakers"], ["/track-record", "Track record"], ["/tarifs", "Tarifs"], ["/mentions-legales", "Mentions légales"], ["/cgu", "CGU"]];
  return (
    <footer className="bg-grey border-t border-line text-muted text-xs leading-relaxed">
      <div className="site py-10">
        <div className="mb-4 flex flex-wrap gap-x-7 gap-y-2 font-medium text-ink">{links.map(([h, l]) => <Link key={h} href={h}>{l}</Link>)}</div>
        <p>{warning} Interdit aux mineurs. RushPlay est un service d'information indépendant, pas un opérateur de paris. Les cotes affichées sont relevées auprès des opérateurs agréés par l'ANJ et peuvent avoir changé.</p>
      </div>
    </footer>
  );
}
```

- [ ] **Step 3 : lancer, build, commit**

Run : `npm test` → tous verts. `npm run build` → OK (les composants serveur `Nav`/`Footer` sont async : supporté par Next 16).

```bash
git add -A && git commit -m "feat(front): Nav, Footer avec ANJ, BigNumber animé, Bars, Reserved, MatchRow, Reveal, session"
```

---

### Task 3 : Accueil et photos

**Files:**
- Create: `app/page.tsx`, `public/photos/stade-nuit.webp`, `public/photos/stade-nuit-900.webp`, `public/photos/stade-jour.webp`, `public/photos/stade-jour-900.webp`, `components/Hero.tsx`, `components/TrackTeaser.tsx`
- Test: `tests/pages.home.test.tsx`

**Interfaces:**
- `Hero({ match })` : eyebrow (équipes, heure, référence), `BigNumber` 236 px, titre « {label} favori. D'après le marché, pas d'après nous. », paragraphe, deux liens. Sans match du jour : titre « On ne prédit rien. On lit le marché. », pas de chiffre.
- Accueil : `getUser()` → `api.matches({ date: parisDate() }, token)` ; match phare = plus grand `best_gap.gap` si Pro, sinon premier ; 4 lignes ; manifeste ; teaser track record (`api.trackRecord("F1")` → première ligne).

- [ ] **Step 1 : photos**

Télécharger les deux photos Unsplash des maquettes et les convertir en WebP (Node, sans dépendance système) :

```bash
cd frontend && mkdir -p public/photos && curl -sL "https://images.unsplash.com/photo-1489944440615-453fc2b6a9a9?w=2000&q=75&fm=webp&fit=crop" -o public/photos/stade-nuit.webp && curl -sL "https://images.unsplash.com/photo-1489944440615-453fc2b6a9a9?w=900&q=70&fm=webp&fit=crop" -o public/photos/stade-nuit-900.webp && curl -sL "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=2000&q=70&fm=webp&fit=crop" -o public/photos/stade-jour.webp && curl -sL "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=900&q=65&fm=webp&fit=crop" -o public/photos/stade-jour-900.webp && ls -la public/photos
```

Attendu : quatre fichiers WebP entre 40 Ko et 400 Ko. Ajouter `public/photos/CREDITS.md` : « Photos Unsplash (licence Unsplash), à remplacer avant mise en ligne : Hamburg stadium par [auteur Unsplash], Bernabéu par [auteur Unsplash]. »

- [ ] **Step 2 : test `tests/pages.home.test.tsx`**

Les pages sont des composants serveur async : on les teste en appelant la fonction et en rendant le résultat.

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";

vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => undefined }) }));

const match = { id: "m1", competition: "F1", league: "Ligue 1", home_team: "Lyon", away_team: "Marseille", kickoff_at: "2026-09-13T15:15:00Z", status: "SCHEDULED",
  favourite: { outcome: "home", label: "Lyon", prob: 0.58, source: "pinnacle" }, reference: { home: 0.58, draw: 0.24, away: 0.18 }, best_gap: null, movement: null, odds_taken_at: "2026-09-13T10:00:00Z", locked: true };

describe("accueil", () => {
  it("héros avec le match phare et quatre lignes", async () => {
    server.use(
      http.get(`${API}/api/v1/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [match, { ...match, id: "m2", home_team: "Lens", away_team: "Lille" }], pagination: { page: 1, limit: 50, total: 2 } } })),
      http.get(`${API}/api/v1/track-record`, () => HttpResponse.json({ success: true, message: "", data: { items: [{ competition: "F1", played: 72, favourite_won: 39, favourite_rate: 0.542 }], note: "n" } })),
    );
    const Page = (await import("@/app/page")).default;
    render(await Page());
    expect(screen.getByText("Lyon favori. D'après le marché, pas d'après nous.")).toBeInTheDocument();
    expect(screen.getByText("Aujourd'hui.")).toBeInTheDocument();
    expect(screen.getByText("Lens – Lille")).toBeInTheDocument();
    expect(screen.getByText("On ne prédit rien.")).toBeInTheDocument();
    expect(screen.getByText(/des favoris ont gagné cette saison en Ligue 1/)).toBeInTheDocument();
  });
  it("sans match du jour : titre générique", async () => {
    server.use(
      http.get(`${API}/api/v1/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [], pagination: { page: 1, limit: 50, total: 0 } } })),
      http.get(`${API}/api/v1/track-record`, () => HttpResponse.json({ success: true, message: "", data: { items: [], note: "n" } })),
    );
    const Page = (await import("@/app/page")).default;
    render(await Page());
    expect(screen.getByText("On ne prédit rien. On lit le marché.")).toBeInTheDocument();
    expect(screen.getByText("Aucun match aujourd'hui. Reviens demain.")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3 : composants et page**

`components/Hero.tsx` :
```tsx
import Link from "next/link";
import type { MatchSummary } from "@/lib/types";
import { BigNumber } from "./BigNumber";
import { formatPctInt, formatTimeFr } from "@/lib/format";

export function Hero({ match }: { match: MatchSummary | null }) {
  const fav = match?.favourite ?? null;
  return (
    <section className="relative overflow-hidden bg-black text-paper text-center">
      <picture className="absolute inset-0">
        <source media="(max-width: 700px)" srcSet="/photos/stade-nuit-900.webp" />
        <img src="/photos/stade-nuit.webp" alt="" className="h-full w-full object-cover object-[center_40%]" loading="eager" fetchPriority="high" />
      </picture>
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,.72)_0%,rgba(0,0,0,.45)_45%,rgba(0,0,0,.85)_100%)]" />
      <div className="site relative py-24 md:py-36 min-h-[620px] md:min-h-[760px] flex flex-col items-center justify-center">
        {match && fav ? (
          <>
            <div className="text-[15px] font-medium text-[#d1d1d6]">{match.home_team} – {match.away_team} · {formatTimeFr(match.kickoff_at)} · {fav.source === "moyenne" ? "moyenne des bookmakers" : "référence Pinnacle"}</div>
            <div className="num-hero mt-3 [text-shadow:0_10px_60px_rgba(0,0,0,.6)]"><BigNumber value={Number(formatPctInt(fav.prob))} suffix="%" /></div>
            <h1 className="mt-8 max-w-[22ch] text-[30px] md:text-[40px] font-bold leading-[1.08] tracking-[-0.035em]">{fav.label} favori. D'après le marché, pas d'après nous.</h1>
          </>
        ) : (
          <h1 className="max-w-[16ch] text-[44px] md:text-[64px] font-extrabold leading-[1.02] tracking-[-0.045em]">On ne prédit rien. On lit le marché.</h1>
        )}
        <p className="mt-4 max-w-[44ch] text-[17px] md:text-[18px] leading-relaxed text-[#d1d1d6]">RushPlay lit les cotes des bookmakers français, retire leur marge et te montre la probabilité que le marché donne vraiment à chaque issue.</p>
        <div className="mt-7 flex flex-wrap justify-center gap-7 text-[17px] font-medium">
          <Link href="/matchs" className="text-link">Voir les matchs du jour ›</Link>
          <a href="#comment" className="text-link">Comment ça marche ›</a>
        </div>
      </div>
    </section>
  );
}
```

`components/TrackTeaser.tsx` :
```tsx
import Link from "next/link";
import type { TrackRow } from "@/lib/types";
import { BigNumber } from "./BigNumber";
import { COMPETITIONS } from "@/lib/types";
export function TrackTeaser({ row }: { row: TrackRow | null }) {
  if (!row) return null;
  return (
    <section className="bg-grey">
      <div className="site grid gap-10 py-20 md:grid-cols-2 md:items-center md:py-24">
        <div className="num-page"><BigNumber value={Math.round(row.favourite_rate * 100)} suffix="%" /></div>
        <p className="text-[20px] md:text-[22px] leading-snug">des favoris ont gagné cette saison en {COMPETITIONS[row.competition] ?? row.competition}. <span className="text-muted">C'est le marché, pas nous. Un favori à 58 % perd ou fait nul quatre fois sur dix. <Link href="/track-record" className="text-link">Le track record complet, match par match ›</Link></span></p>
      </div>
    </section>
  );
}
```

`app/page.tsx` :
```tsx
import Link from "next/link";
import { api } from "@/lib/api";
import { getToken, getUser, isPro } from "@/lib/session";
import { parisDate } from "@/lib/format";
import { Hero } from "@/components/Hero";
import { MatchRow } from "@/components/MatchRow";
import { TrackTeaser } from "@/components/TrackTeaser";
import { Reveal } from "@/components/Reveal";

export const revalidate = 60;

export default async function Home() {
  const [token, user] = [await getToken(), await getUser()];
  const { items } = await api.matches({ date: parisDate(), limit: 50 }, token);
  const withFav = items.filter((m) => m.favourite);
  const star = isPro(user)
    ? [...withFav].sort((a, b) => (b.best_gap?.gap ?? -1) - (a.best_gap?.gap ?? -1))[0] ?? null
    : withFav[0] ?? null;
  let track = null;
  try { track = (await api.trackRecord("F1")).items[0] ?? null; } catch { track = null; }

  return (
    <>
      <Hero match={star} />
      <section className="site py-20 md:py-24">
        <h2 className="h-section">Aujourd'hui.</h2>
        <p className="mt-3 mb-10 max-w-[52ch] text-[19px] text-muted">Le favori de chaque match et sa probabilité, sans compte. Les écarts entre bookmakers et le mouvement des cotes, pour les abonnés.</p>
        {items.length === 0 ? <p className="hair py-10 text-[19px]">Aucun match aujourd'hui. Reviens demain.</p> : (
          <div className="border-b border-line">{items.slice(0, 4).map((m) => <MatchRow key={m.id} match={m} />)}</div>
        )}
        <Link href="/matchs" className="link mt-7 inline-block text-[17px]">Tous les matchs du jour ›</Link>
      </section>
      <section id="comment" className="relative bg-black text-paper">
        <img src="/photos/stade-jour.webp" alt="" className="absolute inset-0 h-full w-full object-cover opacity-[.14]" loading="lazy" />
        <Reveal className="site relative py-24 md:py-28">
          <h2 className="h-section text-[48px] md:text-[72px] max-w-[14ch]">On ne prédit rien.<br /><span className="text-muted">On lit le marché.</span></h2>
          <div className="mt-14 grid gap-8 md:grid-cols-3">
            {[["On relève.", "Les cotes 1N2 de Betclic, Winamax, Unibet, PMU, NetBet et Pinnacle, plusieurs fois par jour. Chaque relevé est conservé."],
              ["On retire la marge.", "Un bookmaker vend toujours plus de 100 %. Ce qui reste une fois sa marge retirée, c'est la probabilité que le marché donne à chaque issue."],
              ["On te montre.", "Le favori, les écarts entre bookmakers, le mouvement depuis le premier relevé. Aucun bonus, aucune magie. Toi, tu décides."]].map(([t, p]) => (
              <div key={t} className="hair-dark pt-7"><b className="block font-tight text-[24px] font-bold tracking-[-0.03em]">{t}</b><p className="mt-2.5 text-[16px] leading-relaxed text-faint">{p}</p></div>
            ))}
          </div>
        </Reveal>
      </section>
      <TrackTeaser row={track} />
    </>
  );
}
```

- [ ] **Step 4 : lancer, vérifier dans le navigateur, committer**

Run : `npm test` → verts. `npm run build` → OK. Puis, avec le backend lancé (`cd backend && uvicorn app.main:app --port 8000`, base SQLite vide acceptable : la page affiche « Aucun match aujourd'hui »), `npm run dev` et ouvrir `http://localhost:3000` : héros, photo, sections, pied de page avec ANJ. Capturer une capture d'écran pour le rapport.

```bash
git add -A && git commit -m "feat(front): accueil — héros photo avec le match phare, matchs du jour, manifeste, teaser track record"
```

---

### Task 4 : Liste des matchs

**Files:**
- Create: `app/matchs/page.tsx`, `components/DayPicker.tsx`, `components/CompetitionFilter.tsx`
- Test: `tests/pages.matchs.test.tsx`

**Interfaces:**
- `/matchs?date=YYYY-MM-DD&competition=E0` : titre « Matchs. », sous-titre « {jour long} · {n} matchs · relevé de {heure du dernier odds_taken_at} », `DayPicker` (7 jours à partir d'aujourd'hui, liens), `CompetitionFilter` (pilules, liens), lignes groupées par compétition dans l'ordre F1, E0, SP1, D1, I1, CL.

- [ ] **Step 1 : test**

```tsx
// tests/pages.matchs.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => undefined }) }));
const m = (id: string, competition: string, league: string, home: string, away: string) => ({ id, competition, league, home_team: home, away_team: away, kickoff_at: "2026-09-13T15:15:00Z", status: "SCHEDULED",
  favourite: { outcome: "home", label: home, prob: 0.55, source: "pinnacle" }, reference: { home: 0.55, draw: 0.25, away: 0.2 }, best_gap: null, movement: null, odds_taken_at: "2026-09-13T10:00:00Z", locked: true });
describe("liste des matchs", () => {
  it("groupe par compétition et affiche le sous-titre", async () => {
    let query = "";
    server.use(http.get(`${API}/api/v1/matches`, ({ request }) => { query = new URL(request.url).search; return HttpResponse.json({ success: true, message: "", data: { items: [m("1", "E0", "Premier League", "Arsenal", "Chelsea"), m("2", "F1", "Ligue 1", "Lyon", "Marseille")], pagination: { page: 1, limit: 200, total: 2 } } }); }));
    const Page = (await import("@/app/matchs/page")).default;
    render(await Page({ searchParams: Promise.resolve({ date: "2026-09-13", competition: undefined }) }));
    expect(query).toContain("date=2026-09-13");
    expect(screen.getByText("Matchs.")).toBeInTheDocument();
    expect(screen.getByText(/2 matchs · relevé de/)).toBeInTheDocument();
    const headings = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(headings).toEqual(["Ligue 1", "Premier League"]);
  });
  it("vide : phrase d'invitation", async () => {
    server.use(http.get(`${API}/api/v1/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [], pagination: { page: 1, limit: 200, total: 0 } } })));
    const Page = (await import("@/app/matchs/page")).default;
    render(await Page({ searchParams: Promise.resolve({ date: "2026-09-13", competition: "CL" }) }));
    expect(screen.getByText("Aucun match ce jour-là pour cette compétition.")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2 : composants et page**

`components/DayPicker.tsx` :
```tsx
import Link from "next/link";
import { formatDayShort, parisDate } from "@/lib/format";
export function DayPicker({ selected, competition }: { selected: string; competition?: string }) {
  const days = Array.from({ length: 7 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() + i); return parisDate(d); });
  return (
    <div className="flex rounded-[10px] bg-[#e8e8ed] p-[3px]">
      {days.map((d) => (
        <Link key={d} href={`/matchs?date=${d}${competition ? `&competition=${competition}` : ""}`} className={`flex-1 rounded-lg py-1.5 text-center text-[12px] font-semibold capitalize ${d === selected ? "bg-paper text-ink shadow-sm" : "text-muted"}`}>{formatDayShort(`${d}T12:00:00Z`)}</Link>
      ))}
    </div>
  );
}
```

`components/CompetitionFilter.tsx` :
```tsx
import Link from "next/link";
import { COMPETITIONS } from "@/lib/types";
export function CompetitionFilter({ date, selected }: { date: string; selected?: string }) {
  const all = [["", "Tous"], ...Object.entries(COMPETITIONS)];
  return (
    <div className="flex gap-2 overflow-x-auto py-3">
      {all.map(([code, label]) => (
        <Link key={code} href={`/matchs?date=${date}${code ? `&competition=${code}` : ""}`} className={`flex-none rounded-full px-3 py-1.5 text-[12px] font-semibold ${(selected ?? "") === code ? "bg-ink text-paper" : "bg-paper text-ink"}`}>{label}</Link>
      ))}
    </div>
  );
}
```

`app/matchs/page.tsx` :
```tsx
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import { formatDateFr, formatTimeFr, parisDate } from "@/lib/format";
import { COMPETITIONS } from "@/lib/types";
import { DayPicker } from "@/components/DayPicker";
import { CompetitionFilter } from "@/components/CompetitionFilter";
import { MatchRow } from "@/components/MatchRow";

export const revalidate = 60;
const ORDER = ["F1", "E0", "SP1", "D1", "I1", "CL"];

export default async function Matchs({ searchParams }: { searchParams: Promise<{ date?: string; competition?: string }> }) {
  const { date = parisDate(), competition } = await searchParams;
  const token = await getToken();
  const { items } = await api.matches({ date, competition, limit: 200 }, token);
  const latest = items.map((m) => m.odds_taken_at).filter(Boolean).sort().at(-1);
  const groups = ORDER.map((c) => [c, items.filter((m) => m.competition === c)] as const).filter(([, ms]) => ms.length);
  return (
    <section className="site py-14 md:py-20">
      <h1 className="h-section">Matchs.</h1>
      <p className="mt-2 mb-6 text-[15px] text-muted capitalize-first">{formatDateFr(`${date}T12:00:00Z`).split(",")[0]} · {items.length} match{items.length > 1 ? "s" : ""}{latest ? ` · relevé de ${formatTimeFr(latest)}` : ""}</p>
      <DayPicker selected={date} competition={competition} />
      <CompetitionFilter date={date} selected={competition} />
      {groups.length === 0 ? <p className="hair mt-6 py-10 text-[19px]">Aucun match ce jour-là pour cette compétition.</p> : groups.map(([code, ms]) => (
        <div key={code} className="mt-10">
          <h3 className="eyebrow mb-2">{COMPETITIONS[code]}</h3>
          <div className="border-b border-line">{ms.map((m) => <MatchRow key={m.id} match={m} />)}</div>
        </div>
      ))}
    </section>
  );
}
```

- [ ] **Step 3 : lancer, build, commit**

`npm test`, `npm run build` verts.
```bash
git add -A && git commit -m "feat(front): liste des matchs par jour et compétition"
```

---

### Task 5 : Page match

**Files:**
- Create: `app/matchs/[id]/page.tsx`, `components/MovementChart.tsx`, `components/BookTable.tsx`, `components/FormTable.tsx`
- Test: `tests/pages.match.test.tsx`

**Interfaces:**
- `MovementChart({ history, favourite })` : SVG 520×200, une polyligne de la probabilité de référence du favori, point final, deux étiquettes (premier et dernier relevé : jour court + %).
- `BookTable({ books, reference_book })` : Pinnacle en gras en tête, puis les FR ; colonnes Book / 1 / N / 2 / Marge ; la cote de l'issue favorite porte une pastille `+x,x %` quand l'écart est ≥ 0,03.
- `FormTable({ form, h2h, home, away })` : Équipe / 5 derniers (V N D) / Buts ; puis face-à-face.
- Page : anonyme ou Starter → `Reserved` à la place du tableau, de la courbe et de la colonne des pastilles ; Pro → tout.

- [ ] **Step 1 : test**

```tsx
// tests/pages.match.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => undefined }) }));
const detail = (locked: boolean) => ({ id: "m1", competition: "F1", league: "Ligue 1", home_team: "Lyon", away_team: "Marseille", kickoff_at: "2026-09-13T15:15:00Z", status: "SCHEDULED",
  favourite: { outcome: "home", label: "Lyon", prob: 0.58, source: "pinnacle" }, reference: { home: 0.58, draw: 0.24, away: 0.18 },
  best_gap: locked ? null : { bookmaker: "betclic_fr", outcome: "home", gap: 0.032, odds: 1.78 }, movement: locked ? null : { home: 3.1, draw: -1, away: -2.1 }, odds_taken_at: "2026-09-13T10:00:00Z", locked,
  books: locked ? null : [{ bookmaker: "betclic_fr", label: "Betclic", home: 1.78, draw: 3.9, away: 4.8, margin: 0.071, gaps: { home: 0.032, draw: -0.06, away: -0.14 } }],
  reference_book: locked ? null : { bookmaker: "pinnacle", label: "Pinnacle", home: 1.72, draw: 4.0, away: 5.0, margin: 0.024 },
  history: locked ? null : [{ taken_at: "2026-09-08T08:00:00Z", reference: { home: 0.55, draw: 0.25, away: 0.2 } }, { taken_at: "2026-09-13T10:00:00Z", reference: { home: 0.58, draw: 0.24, away: 0.18 } }],
  form: { home: { played: 5, wins: 3, draws: 1, losses: 1, goals_for: 7, goals_against: 4, sequence: "VVNDV" }, away: { played: 5, wins: 1, draws: 2, losses: 2, goals_for: 4, goals_against: 6, sequence: "DNVDN" } },
  h2h: [{ kickoff_at: "2026-03-01T20:00:00Z", home: "Lyon", away: "Marseille", score: "1-1" }],
  analysis: locked ? "Lyon est favori à 58 %. Lyon reste sur trois victoires lors des cinq derniers matchs ; Marseille sur une seule." : "Lyon est favori à 58 %. Betclic paie 1,78 sur Lyon, soit 3,2 % au-dessus de la référence.", result: null });
describe("page match", () => {
  it("abonné : tableau, courbe, analyse complète", async () => {
    server.use(http.get(`${API}/api/v1/matches/m1`, () => HttpResponse.json({ success: true, message: "", data: detail(false) })));
    const Page = (await import("@/app/matchs/[id]/page")).default;
    render(await Page({ params: Promise.resolve({ id: "m1" }) }));
    expect(screen.getByText("Lyon")).toBeInTheDocument();
    expect(screen.getByText("Bookmakers")).toBeInTheDocument();
    expect(screen.getByText("Pinnacle")).toBeInTheDocument();
    expect(screen.getByText("+3,2 %")).toBeInTheDocument();
    expect(screen.getByText("Mouvement")).toBeInTheDocument();
    expect(screen.getByText(/Betclic paie 1,78/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Noter ce pari" })).toBeInTheDocument();
  });
  it("anonyme : bloc réservé, pas de tableau, analyse publique", async () => {
    server.use(http.get(`${API}/api/v1/matches/m1`, () => HttpResponse.json({ success: true, message: "", data: detail(true) })));
    const Page = (await import("@/app/matchs/[id]/page")).default;
    render(await Page({ params: Promise.resolve({ id: "m1" }) }));
    expect(screen.getAllByText(/Réservé aux abonnés/).length).toBeGreaterThan(0);
    expect(screen.queryByText("Pinnacle")).not.toBeInTheDocument();
    expect(screen.getByText(/trois victoires/)).toBeInTheDocument();
  });
  it("introuvable : notFound", async () => {
    server.use(http.get(`${API}/api/v1/matches/zz`, () => HttpResponse.json({ success: false, message: "Match not found" }, { status: 404 })));
    const Page = (await import("@/app/matchs/[id]/page")).default;
    await expect(Page({ params: Promise.resolve({ id: "zz" }) })).rejects.toThrow();
  });
});
```

Le dernier test attend que `notFound()` de Next lève (il lève une erreur spéciale) : c'est le comportement de `next/navigation` hors runtime Next ; ne pas le mocker.

- [ ] **Step 2 : composants**

`components/MovementChart.tsx` :
```tsx
import type { Outcome, Probs } from "@/lib/types";
import { formatDayShort, formatPct } from "@/lib/format";
export function MovementChart({ history, favourite }: { history: { taken_at: string; reference: Probs }[]; favourite: Outcome }) {
  if (history.length < 2) return <p className="hair py-6 text-[15px] text-muted">Un seul relevé pour l'instant : le mouvement apparaîtra au prochain.</p>;
  const ys = history.map((h) => h.reference[favourite]);
  const min = Math.min(...ys) - 0.02, max = Math.max(...ys) + 0.02;
  const pts = ys.map((y, i) => [ (i / (ys.length - 1)) * 520, 190 - ((y - min) / (max - min)) * 150 ] as const);
  const path = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const first = history[0], last = history[history.length - 1];
  return (
    <svg viewBox="0 0 520 200" className="mt-6 h-[200px] w-full" role="img" aria-label={`Probabilité du favori de ${formatPct(ys[0])} à ${formatPct(ys[ys.length - 1])}`}>
      <line x1="0" y1="199" x2="520" y2="199" stroke="rgba(0,0,0,.12)" />
      <polyline points={path} fill="none" stroke="#1d1d1f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="5" fill="#1d1d1f" />
      <text x="0" y="186" fontSize="13" fill="#6e6e73">{formatDayShort(first.taken_at)} · {formatPct(ys[0])}</text>
      <text x="520" y={Math.max(14, pts[pts.length - 1][1] - 14)} fontSize="13" fill="#1d1d1f" fontWeight="600" textAnchor="end">{formatDayShort(last.taken_at)} · {formatPct(ys[ys.length - 1])}</text>
    </svg>
  );
}
```

`components/BookTable.tsx` :
```tsx
import type { Book, MatchDetail, Outcome } from "@/lib/types";
import { formatGap, formatMargin, formatOdds } from "@/lib/format";
const cell = (b: Book, k: Outcome, fav: Outcome | null) => (
  <td className={`py-4 text-right tabular-nums border-b border-line ${k === fav ? "font-bold" : ""}`}>{formatOdds(b[k])}{k === fav && b.gaps[k] >= 0.03 ? <span className="ml-2 rounded-full bg-ink px-2 py-[1px] text-[12px] font-semibold text-paper">{formatGap(b.gaps[k])}</span> : null}</td>
);
export function BookTable({ books, reference_book, favourite }: { books: Book[]; reference_book: MatchDetail["reference_book"]; favourite: Outcome | null }) {
  return (
    <table className="mt-8 w-full border-collapse text-[16px]">
      <thead><tr>{["Book", "1", "N", "2", "Marge"].map((h, i) => <th key={h} className={`border-b border-ink pb-3 text-[12px] font-semibold uppercase tracking-[0.06em] text-muted ${i ? "text-right" : "text-left"}`}>{h}</th>)}</tr></thead>
      <tbody>
        {reference_book && <tr><td className="py-4 font-bold border-b border-line">{reference_book.label}</td>{(["home", "draw", "away"] as Outcome[]).map((k) => <td key={k} className="py-4 text-right tabular-nums border-b border-line">{formatOdds(reference_book[k])}</td>)}<td className="py-4 text-right tabular-nums border-b border-line">{formatMargin(reference_book.margin)}</td></tr>}
        {books.map((b) => <tr key={b.bookmaker}><td className="py-4 border-b border-line">{b.label}</td>{cell(b, "home", favourite)}{cell(b, "draw", favourite)}{cell(b, "away", favourite)}<td className="py-4 text-right tabular-nums border-b border-line">{formatMargin(b.margin)}</td></tr>)}
      </tbody>
    </table>
  );
}
```

`components/FormTable.tsx` :
```tsx
import type { Form, H2H } from "@/lib/types";
import { formatDayShort } from "@/lib/format";
export function FormTable({ form, h2h, home, away }: { form: { home: Form; away: Form }; h2h: H2H[]; home: string; away: string }) {
  const seq = (s: string) => s.split("").join(" ");
  const row = (name: string, f: Form) => <tr><td className="py-4 font-bold border-b border-line">{name}</td><td className="py-4 tracking-[0.12em] border-b border-line">{f.played ? seq(f.sequence) : "—"}</td><td className="py-4 text-right tabular-nums border-b border-line">{f.played ? `${f.goals_for} – ${f.goals_against}` : "—"}</td></tr>;
  return (
    <>
      <table className="mt-4 w-full border-collapse text-[16px]">
        <thead><tr><th className="border-b border-ink pb-3 text-left text-[12px] font-semibold uppercase tracking-[0.06em] text-muted">Équipe</th><th className="border-b border-ink pb-3 text-left text-[12px] font-semibold uppercase tracking-[0.06em] text-muted">5 derniers</th><th className="border-b border-ink pb-3 text-right text-[12px] font-semibold uppercase tracking-[0.06em] text-muted">Buts</th></tr></thead>
        <tbody>{row(home, form.home)}{row(away, form.away)}</tbody>
      </table>
      {h2h.length > 0 && <p className="mt-4 text-[14px] text-muted">Face-à-face : {h2h.map((m) => `${m.home} ${m.score} ${m.away} (${formatDayShort(m.kickoff_at)})`).join(", ")}</p>}
    </>
  );
}
```

- [ ] **Step 3 : page `app/matchs/[id]/page.tsx`**

```tsx
import Link from "next/link";
import { notFound } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { getToken } from "@/lib/session";
import { formatDateFr, formatPctInt, formatSigned } from "@/lib/format";
import { COMPETITIONS } from "@/lib/types";
import { BigNumber } from "@/components/BigNumber";
import { Bars } from "@/components/Bars";
import { Reserved } from "@/components/Reserved";
import { BookTable } from "@/components/BookTable";
import { MovementChart } from "@/components/MovementChart";
import { FormTable } from "@/components/FormTable";

export const revalidate = 60;

export default async function Match({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const token = await getToken();
  let m;
  try { m = await api.match(id, token); } catch (e) { if (e instanceof ApiError && e.status === 404) notFound(); throw e; }
  const fav = m.favourite;
  const mv = m.movement && fav ? m.movement[fav.outcome] : null;
  return (
    <section className="site py-14 md:py-20">
      <div className="text-[14px] text-muted"><Link href="/matchs">Matchs</Link> › {COMPETITIONS[m.competition] ?? m.league}</div>
      <h1 className="mt-4 font-tight text-[44px] md:text-[96px] font-extrabold leading-[0.95] tracking-[-0.06em]">{m.home_team} <span className="text-faint">– {m.away_team}</span></h1>
      <p className="mt-3 text-[16px] text-muted">{formatDateFr(m.kickoff_at)} · {fav ? (fav.source === "moyenne" ? "moyenne des bookmakers, Pinnacle absent" : "référence Pinnacle") : "pas encore de relevé"}{m.odds_taken_at ? ` · relevé de ${formatDateFr(m.odds_taken_at).split(", ")[1]}` : ""}</p>
      {m.result && <p className="mt-2 text-[16px] font-semibold">Terminé : {m.home_team} {m.result.home} – {m.result.away} {m.away_team}</p>}

      <div className="mt-12 grid gap-12 md:grid-cols-2 md:gap-16">
        <div>
          {fav && m.reference ? (
            <>
              <div className="num-page"><BigNumber value={Number(formatPctInt(fav.prob))} suffix="%" /></div>
              <div className="mt-4 text-[20px] font-semibold">{fav.label} favori {mv !== null && <span className="text-muted font-medium">· {mv >= 0 ? "▲" : "▼"} {formatSigned(mv, " pts").slice(1)} depuis le premier relevé</span>}</div>
              <Bars probs={m.reference} favourite={fav.outcome} home={m.home_team} away={m.away_team} />
            </>
          ) : <p className="text-[19px] text-muted">Pas encore de relevé de cotes pour ce match.</p>}
        </div>
        <div>
          {m.analysis && m.analysis.split(". ").reduce<string[][]>((acc, s, i) => { (i < 2 ? acc[0] : acc[1]).push(s); return acc; }, [[], []]).map((part, i) => part.length ? <p key={i} className={`text-[20px] md:text-[22px] leading-snug tracking-[-0.01em] ${i ? "mt-4 text-muted" : ""}`}>{part.join(". ").replace(/\.?$/, ".")}</p> : null)}
          <Link href={`/carnet?match=${m.id}`} className="btn mt-9">Noter ce pari</Link>
        </div>
      </div>

      <div className="mt-20 grid gap-12 md:grid-cols-2 md:gap-16">
        <div>
          <h3 className="h-sub">Bookmakers</h3>
          {m.locked || !m.books ? <div className="mt-6"><Reserved /></div> : <BookTable books={m.books} reference_book={m.reference_book} favourite={fav?.outcome ?? null} />}
        </div>
        <div>
          <h3 className="h-sub">Mouvement</h3>
          {m.locked || !m.history ? <div className="mt-6"><Reserved what="aux abonnés, relevé par relevé" /></div> : fav ? <MovementChart history={m.history} favourite={fav.outcome} /> : null}
          <h3 className="h-sub mt-10">Forme</h3>
          <FormTable form={m.form} h2h={m.h2h} home={m.home_team} away={m.away_team} />
        </div>
      </div>
    </section>
  );
}
```

Simplifier la découpe de l'analyse si elle gêne : afficher le texte entier en un paragraphe de 22 px est acceptable ; l'objectif est deux paragraphes (première phrase en encre, suite en `muted`) — implémenter au plus simple qui passe les tests.

- [ ] **Step 4 : lancer, build, commit**

`npm test`, `npm run build` verts. Vérifier dans le navigateur avec un match réel si le backend a des données (sinon capture du test).
```bash
git add -A && git commit -m "feat(front): page match — chiffre, barres, analyse, bookmakers, mouvement, forme, paywall"
```

*(Suite : Tasks 6 à 10 — session et compte, bookmakers et tarifs, carnet, track record, finitions — dans `2026-09-10-rushplay-front-2.md`.)*
