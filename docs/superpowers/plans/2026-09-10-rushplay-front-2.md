# RushPlay front — plan d'exécution, partie 2 (session, compte, bookmakers, tarifs, carnet, track record, finitions)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Suite de `2026-09-10-rushplay-front.md` (Tasks 1 à 5) : mêmes contraintes globales et même structure de fichiers.

**Goal, Architecture, Tech Stack, Global Constraints :** identiques à la partie 1. Rappel : aucune couleur hors jetons, pas de boîtes, vocabulaire interdit (`prédiction`, `pronostic`, `value bet`, `confiance`), ANJ dans chaque pied de page, `npm test` et `npm run build` verts avant chaque commit.

---

### Task 6 : Session (cookie), connexion, inscription à 18 ans, compte

**Files:**
- Create: `app/api/session/route.ts`, `app/connexion/page.tsx`, `app/inscription/page.tsx`, `app/compte/page.tsx`, `components/AuthForm.tsx`, `lib/client-session.ts`
- Test: `tests/auth.test.tsx`

**Interfaces:**
- `POST /api/session` body `{ token }` → pose le cookie `rp_token` (`httpOnly`, `sameSite=lax`, `secure` en production, 7 jours) ; `DELETE /api/session` → supprime. Route handler Next, côté serveur.
- `lib/client-session.ts` : `saveSession(token)` (POST) et `clearSession()` (DELETE) appelés depuis les formulaires client, puis `router.push`.
- `AuthForm({ mode: "login" | "signup" })` : client ; champs prénom (signup), e-mail, mot de passe, date de naissance (signup) + case « J'ai 18 ans ou plus » (signup) ; appelle `api.login`/`api.signup`, affiche `ApiError.message` sous le formulaire, puis `saveSession` et redirection vers `/matchs`.
- `/compte` : serveur ; sans session → redirection `/connexion` ; sinon prénom, e-mail, plan (« Gratuit » / « Lecture complète »), lien tarifs si Starter, bouton « Se déconnecter » (client, `clearSession` puis `/`).

- [ ] **Step 1 : tests**

```tsx
// tests/auth.test.tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, refresh: vi.fn() }) }));
vi.mock("@/lib/client-session", () => ({ saveSession: vi.fn(async () => {}), clearSession: vi.fn(async () => {}) }));

describe("AuthForm", () => {
  it("connexion : appelle l'API, sauvegarde la session, redirige", async () => {
    server.use(http.post(`${API}/api/v1/auth/login`, () => HttpResponse.json({ success: true, message: "", data: { access_token: "tok", token_type: "bearer", user: { id: "u", first_name: "Lucas", email: "l@t.fr", role: "USER", subscription_plan: "STARTER" } } })));
    const { AuthForm } = await import("@/components/AuthForm");
    const { saveSession } = await import("@/lib/client-session");
    render(<AuthForm mode="login" />);
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "l@t.fr" } });
    fireEvent.change(screen.getByLabelText("Mot de passe"), { target: { value: "motdepasse123" } });
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    await waitFor(() => expect(saveSession).toHaveBeenCalledWith("tok"));
    expect(push).toHaveBeenCalledWith("/matchs");
  });
  it("inscription refusée avant 18 ans : le message de l'API s'affiche", async () => {
    server.use(http.post(`${API}/api/v1/auth/signup`, () => HttpResponse.json({ detail: [{ loc: ["body", "birth_date"], msg: "Value error, Vous devez avoir 18 ans ou plus" }] }, { status: 422 })));
    const { AuthForm } = await import("@/components/AuthForm");
    render(<AuthForm mode="signup" />);
    fireEvent.change(screen.getByLabelText("Prénom"), { target: { value: "Jeune" } });
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "j@t.fr" } });
    fireEvent.change(screen.getByLabelText("Mot de passe"), { target: { value: "motdepasse123" } });
    fireEvent.change(screen.getByLabelText("Date de naissance"), { target: { value: "2015-01-01" } });
    fireEvent.click(screen.getByLabelText(/J'ai 18 ans ou plus/));
    fireEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));
    expect(await screen.findByText("Vous devez avoir 18 ans ou plus")).toBeInTheDocument();
  });
  it("inscription : le bouton reste désactivé tant que la case 18 ans n'est pas cochée", async () => {
    const { AuthForm } = await import("@/components/AuthForm");
    render(<AuthForm mode="signup" />);
    expect(screen.getByRole("button", { name: "Créer mon compte" })).toBeDisabled();
  });
});
```

- [ ] **Step 2 : code**

`app/api/session/route.ts` :
```ts
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
const NAME = "rp_token";
export async function POST(req: Request) {
  const { token } = (await req.json()) as { token?: string };
  if (!token || typeof token !== "string") return NextResponse.json({ ok: false }, { status: 400 });
  (await cookies()).set(NAME, token, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: 60 * 60 * 24 * 7 });
  return NextResponse.json({ ok: true });
}
export async function DELETE() {
  (await cookies()).delete(NAME);
  return NextResponse.json({ ok: true });
}
```

`lib/client-session.ts` :
```ts
export async function saveSession(token: string) { await fetch("/api/session", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) }); }
export async function clearSession() { await fetch("/api/session", { method: "DELETE" }); }
```

`components/AuthForm.tsx` :
```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { saveSession } from "@/lib/client-session";

const field = "mt-2 w-full border-0 border-b border-ink bg-transparent py-2 text-[17px] font-medium outline-none focus:border-b-2";
const label = "block text-[12px] font-semibold uppercase tracking-[0.04em] text-muted";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const [f, setF] = useState({ first_name: "", email: "", password: "", birth_date: "", adult: false });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const signup = mode === "signup";
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null);
    try {
      const data = signup ? await api.signup({ first_name: f.first_name, email: f.email, password: f.password, birth_date: f.birth_date }) : await api.login(f.email, f.password);
      await saveSession(data.access_token);
      router.push("/matchs"); router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de joindre le service. Réessaie dans un instant.");
    } finally { setBusy(false); }
  }

  return (
    <form onSubmit={submit} className="max-w-[420px]">
      {signup && <div className="mt-6"><label className={label} htmlFor="first_name">Prénom</label><input id="first_name" className={field} value={f.first_name} onChange={set("first_name")} required minLength={2} autoComplete="given-name" /></div>}
      <div className="mt-6"><label className={label} htmlFor="email">E-mail</label><input id="email" type="email" className={field} value={f.email} onChange={set("email")} required autoComplete="email" /></div>
      <div className="mt-6"><label className={label} htmlFor="password">Mot de passe</label><input id="password" type="password" className={field} value={f.password} onChange={set("password")} required minLength={8} autoComplete={signup ? "new-password" : "current-password"} /></div>
      {signup && <>
        <div className="mt-6"><label className={label} htmlFor="birth_date">Date de naissance</label><input id="birth_date" type="date" className={field} value={f.birth_date} onChange={set("birth_date")} required /></div>
        <label className="mt-6 flex items-start gap-3 text-[14px]"><input type="checkbox" checked={f.adult} onChange={set("adult")} className="mt-1" /><span>J'ai 18 ans ou plus. Les paris sportifs comportent des risques : endettement, dépendance… Appelez le 09 74 75 13 13.</span></label>
      </>}
      {error && <p role="alert" className="mt-5 text-[14px] font-medium">{error}</p>}
      <button type="submit" disabled={busy || (signup && !f.adult)} className="btn mt-8 disabled:opacity-40">{signup ? "Créer mon compte" : "Se connecter"}</button>
      <p className="mt-6 text-[14px] text-muted">{signup ? <>Déjà un compte ? <Link href="/connexion" className="text-link">Se connecter</Link></> : <>Pas encore de compte ? <Link href="/inscription" className="text-link">Créer un compte</Link></>}</p>
    </form>
  );
}
```

`app/connexion/page.tsx` :
```tsx
import { AuthForm } from "@/components/AuthForm";
export default function Connexion() {
  return <section className="site py-16 md:py-24"><h1 className="h-section">Se connecter.</h1><AuthForm mode="login" /></section>;
}
```

`app/inscription/page.tsx` :
```tsx
import { AuthForm } from "@/components/AuthForm";
export default function Inscription() {
  return <section className="site py-16 md:py-24"><h1 className="h-section">Créer un compte.</h1><p className="mt-3 max-w-[48ch] text-[17px] text-muted">Gratuit. Le favori de chaque match, sans limite. Réservé aux 18 ans et plus.</p><AuthForm mode="signup" /></section>;
}
```

`components/LogoutButton.tsx` :
```tsx
"use client";
import { useRouter } from "next/navigation";
import { clearSession } from "@/lib/client-session";
export function LogoutButton() {
  const router = useRouter();
  return <button className="btn-ghost mt-8" onClick={async () => { await clearSession(); router.push("/"); router.refresh(); }}>Se déconnecter</button>;
}
```

`app/compte/page.tsx` :
```tsx
import Link from "next/link";
import { redirect } from "next/navigation";
import { getUser, isPro } from "@/lib/session";
import { LogoutButton } from "@/components/LogoutButton";
export const dynamic = "force-dynamic";
export default async function Compte() {
  const user = await getUser();
  if (!user) redirect("/connexion");
  return (
    <section className="site py-16 md:py-24">
      <h1 className="h-section">{user.first_name}.</h1>
      <dl className="mt-10 max-w-[520px] border-t border-ink text-[17px]">
        {[["E-mail", user.email], ["Offre", isPro(user) ? "Lecture complète" : "Gratuit"]].map(([k, v]) => <div key={k} className="grid grid-cols-[140px_1fr] gap-4 border-b border-line py-4"><dt className="text-muted">{k}</dt><dd className="font-medium">{v}</dd></div>)}
      </dl>
      {!isPro(user) && <Link href="/tarifs" className="link mt-6 inline-block text-[17px]">Passer à la lecture complète ›</Link>}
      <div><LogoutButton /></div>
    </section>
  );
}
```

- [ ] **Step 3 : lancer, build, commit**

`npm test`, `npm run build` verts. Vérifier en navigateur avec le backend : inscription (date < 18 ans → message), connexion, `/compte`, déconnexion.
```bash
git add -A && git commit -m "feat(front): session par cookie, connexion, inscription 18 ans, page compte"
```

---

### Task 7 : Bookmakers (comparateur) et tarifs

**Files:**
- Create: `app/bookmakers/page.tsx`, `app/tarifs/page.tsx`, `lib/pricing.ts`
- Test: `tests/pages.books.test.tsx`

**Interfaces:**
- `/bookmakers` : serveur ; `api.books(token)` ; 403 → afficher le titre, le lead et `Reserved` (pas d'erreur) ; sinon tableau (Bookmaker / Meilleur écart (match + issue, cote, heure) / Écart (40 px) / Écarts ≥ 3 % / Marge moyenne / Matchs), lignes triées par l'API, puis la phrase « Les cotes changent… ».
- `lib/pricing.ts` : `PRICE_MONTHLY = 9`, `PLAN_NAMES = { STARTER: "Gratuit", PRO: "Lecture complète", ELITE: "Lecture complète" }`.
- `/tarifs` : deux colonnes séparées par un filet, listes à filets, boutons : « Créer un compte » (→ `/inscription`, ou `/compte` si connecté) et « S'abonner » (→ `/compte` avec le paramètre `?abonnement=1` : le paiement n'existe pas encore, la page compte affiche « Le paiement arrive bientôt. Écris-nous pour être prévenu. »).

- [ ] **Step 1 : test**

```tsx
// tests/pages.books.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => ({ value: "tok" }) }) }));
describe("bookmakers", () => {
  it("Pro : tableau avec meilleur écart et marge", async () => {
    server.use(
      http.get(`${API}/api/v1/auth/me`, () => HttpResponse.json({ success: true, message: "", data: { id: "u", first_name: "L", email: "l@t.fr", role: "USER", subscription_plan: "PRO" } })),
      http.get(`${API}/api/v1/books`, () => HttpResponse.json({ success: true, message: "", data: { threshold: 0.03, items: [{ bookmaker: "winamax_fr", label: "Winamax", matches: 41, avg_margin: 0.08, gaps_above_threshold: 6, best: { match_id: "m1", home_team: "Real Madrid", away_team: "Séville", kickoff_at: "2026-09-13T19:00:00Z", outcome: "home", gap: 0.041, odds: 1.42 } }] } })),
    );
    const Page = (await import("@/app/bookmakers/page")).default;
    render(await Page());
    expect(screen.getByText("Qui paie le mieux.")).toBeInTheDocument();
    expect(screen.getByText("Winamax")).toBeInTheDocument();
    expect(screen.getByText("Real Madrid – Séville")).toBeInTheDocument();
    expect(screen.getByText("+4,1")).toBeInTheDocument();
    expect(screen.getByText("8,0 %")).toBeInTheDocument();
  });
  it("non Pro : bloc réservé, pas d'erreur", async () => {
    server.use(
      http.get(`${API}/api/v1/auth/me`, () => HttpResponse.json({ success: true, message: "", data: { id: "u", first_name: "L", email: "l@t.fr", role: "USER", subscription_plan: "STARTER" } })),
      http.get(`${API}/api/v1/books`, () => HttpResponse.json({ success: false, message: "Réservé aux abonnés" }, { status: 403 })),
    );
    const Page = (await import("@/app/bookmakers/page")).default;
    render(await Page());
    expect(screen.getAllByText(/Réservé aux abonnés/).length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2 : code**

`lib/pricing.ts` :
```ts
export const PRICE_MONTHLY = 9;
export const PLAN_NAMES: Record<string, string> = { STARTER: "Gratuit", PRO: "Lecture complète", ELITE: "Lecture complète" };
```

`app/bookmakers/page.tsx` :
```tsx
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { getToken } from "@/lib/session";
import { formatDateFr, formatGap, formatMargin, formatOdds } from "@/lib/format";
import { Reserved } from "@/components/Reserved";
import type { BookRow } from "@/lib/types";
export const dynamic = "force-dynamic";
const th = (t: string, right = false) => <th className={`border-b border-ink pb-3 text-[12px] font-semibold uppercase tracking-[0.06em] text-muted ${right ? "text-right" : "text-left"}`}>{t}</th>;
export default async function Bookmakers() {
  const token = await getToken();
  let rows: BookRow[] | null = null;
  try { rows = (await api.books(token)).items; } catch (e) { if (!(e instanceof ApiError && e.status === 403)) throw e; }
  return (
    <section className="site py-14 md:py-20">
      <p className="eyebrow">Bookmakers · 7 prochains jours</p>
      <h1 className="h-section mt-3">Qui paie le mieux.</h1>
      <p className="mt-3 mb-10 max-w-[60ch] text-[19px] text-muted">Pour chaque bookmaker français, l'écart le plus favorable par rapport à la référence Pinnacle sur les matchs à venir, et sa marge moyenne. Un écart positif veut dire qu'il paie plus que ce que le marché implique.</p>
      {rows === null ? <Reserved /> : rows.length === 0 ? <p className="hair py-10 text-[19px]">Aucun relevé de cotes pour les prochains jours.</p> : (
        <table className="w-full border-collapse text-[16px]">
          <thead><tr>{th("Bookmaker")}{th("Meilleur écart")}{th("Écart", true)}{th("Écarts ≥ 3 %", true)}{th("Marge moyenne", true)}{th("Matchs", true)}</tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.bookmaker}>
              <td className="border-b border-line py-5 font-tight text-[24px] font-bold tracking-[-0.03em]">{r.label}</td>
              <td className="border-b border-line py-5 text-[15px]">{r.best ? <><Link href={`/matchs/${r.best.match_id}`} className="block font-semibold">{r.best.home_team} – {r.best.away_team}</Link><span className="text-muted">{r.best.outcome === "home" ? r.best.home_team : r.best.outcome === "away" ? r.best.away_team : "Nul"}, {formatOdds(r.best.odds)} · {formatDateFr(r.best.kickoff_at)}</span></> : "—"}</td>
              <td className="border-b border-line py-5 text-right font-tight text-[40px] font-extrabold tracking-[-0.05em] leading-none">{r.best ? formatGap(r.best.gap).replace(" %", "") : "—"}<span className="font-sans text-[13px] font-medium text-muted"> %</span></td>
              <td className="border-b border-line py-5 text-right tabular-nums">{r.gaps_above_threshold}</td>
              <td className="border-b border-line py-5 text-right tabular-nums">{r.avg_margin === null ? "—" : formatMargin(r.avg_margin)}</td>
              <td className="border-b border-line py-5 text-right tabular-nums">{r.matches}</td>
            </tr>
          ))}</tbody>
        </table>
      )}
      <p className="mt-6 max-w-[70ch] text-[13px] leading-relaxed text-muted">Les cotes changent. Un écart affiché à midi peut avoir disparu à 17 h. RushPlay n'a aucun lien commercial avec les bookmakers cités.</p>
    </section>
  );
}
```

Le test attend `"+4,1"` seul : `formatGap(0.041)` donne `"+4,1 %"`, et `.replace(" %", "")` doit retirer l'espace insécable produit par `Intl` — utiliser `.replace(/[\s  ]%$/, "")`.

`app/tarifs/page.tsx` :
```tsx
import Link from "next/link";
import { getUser, isPro } from "@/lib/session";
import { PRICE_MONTHLY } from "@/lib/pricing";
export const dynamic = "force-dynamic";
const li = (t: string, off = false) => <li key={t} className={`border-t border-line py-3 text-[16px] ${off ? "text-faint" : ""}`}>{t}</li>;
export default async function Tarifs() {
  const user = await getUser();
  return (
    <section className="site py-14 md:py-20">
      <p className="eyebrow">Tarifs</p>
      <h1 className="h-section mt-3">Le favori est gratuit.<br />La lecture complète, non.</h1>
      <p className="mt-3 mb-12 max-w-[56ch] text-[19px] text-muted">Sans compte, tu vois chaque jour le favori de chaque match et sa probabilité. L'abonnement ouvre ce que le marché ne dit pas au premier regard.</p>
      <div className="grid border-t border-ink md:grid-cols-2">
        <div className="py-10 md:border-r md:border-line md:pr-10">
          <div className="font-tight text-[34px] font-extrabold tracking-[-0.04em]">Gratuit</div>
          <div className="mt-4 font-tight text-[72px] font-extrabold leading-none tracking-[-0.06em]">0<span className="ml-1 text-[20px] font-medium tracking-normal text-muted">€</span></div>
          <ul className="mt-7 list-none p-0">{["Le favori et sa probabilité, tous les matchs", "L'analyse en trois phrases", "La forme et les face-à-face", "Le track record public"].map((t) => li(t))}{["Les écarts entre bookmakers", "Le mouvement des cotes, relevé par relevé", "Le comparateur", "Le carnet"].map((t) => li(t, true))}</ul>
          {user ? <span className="btn-ghost mt-7 opacity-60">Ton offre actuelle</span> : <Link href="/inscription" className="btn-ghost mt-7">Créer un compte</Link>}
        </div>
        <div className="py-10 md:pl-10">
          <div className="font-tight text-[34px] font-extrabold tracking-[-0.04em]">Lecture complète</div>
          <div className="mt-4 font-tight text-[72px] font-extrabold leading-none tracking-[-0.06em]">{PRICE_MONTHLY}<span className="ml-1 text-[20px] font-medium tracking-normal text-muted">€ / mois</span></div>
          <ul className="mt-7 list-none p-0">{["Tout le gratuit", "Les écarts entre bookmakers, match par match", "Le mouvement des cotes, relevé par relevé", "Le comparateur des bookmakers français", "Le carnet, réglé automatiquement", "Sans engagement, résiliable en un clic"].map((t) => li(t))}</ul>
          {isPro(user) ? <span className="btn mt-7 opacity-60">Ton offre actuelle</span> : <Link href={user ? "/compte?abonnement=1" : "/inscription?abonnement=1"} className="btn mt-7">S'abonner</Link>}
          <p className="mt-4 text-[13px] text-muted">Réservé aux 18 ans et plus. RushPlay ne prend pas de paris et ne touche rien des bookmakers.</p>
        </div>
      </div>
    </section>
  );
}
```

Dans `app/compte/page.tsx`, lire `searchParams` et, si `abonnement=1` et non Pro, afficher au-dessus du `dl` : `<p className="hair py-5 text-[17px]">Le paiement arrive bientôt. Écris-nous à contact@rushplay.fr pour être prévenu.</p>`.

- [ ] **Step 3 : lancer, build, commit**

```bash
git add -A && git commit -m "feat(front): comparateur des bookmakers (Pro) et page des tarifs"
```

---

### Task 8 : Carnet de bankroll

**Files:**
- Create: `app/carnet/page.tsx`, `components/Bankroll.tsx`, `components/BetForm.tsx`, `components/Kpi.tsx`
- Test: `tests/carnet.test.tsx`

**Interfaces:**
- `/carnet` : serveur ; sans session → `/connexion` ; sinon rend `<Bankroll token={token} preselected={searchParams.match} />` (client). Le jeton est passé au composant client (il est déjà dans le navigateur via le cookie httpOnly, mais le client ne peut pas le lire : on le transmet en prop depuis le serveur, c'est acceptable puisque le composant ne le persiste pas).
- `Bankroll` : charge `api.bankroll.list(token)` ; affiche 4 `Kpi` (Engagé = `stakes`, Réglé = `settled_stakes`, Résultat = `profit`, Rendement = `roi` ou « — »), tableau des paris (statut : En attente / Gagné / Perdu / Annulé), actions : « Supprimer » (PENDING), « Annuler » (PENDING sur match reporté) ; `BetForm` en bas.
- `BetForm({ token, preselected, onSaved })` : champs Match (liste déroulante des matchs des 7 prochains jours via `api.matches({ limit: 200 })`, présélection par id), Pari (Domicile / Nul / Extérieur avec les noms), Bookmaker (liste des 5 FR), Cote, Mise ; bouton « Noter ce pari » ; erreurs de l'API affichées.
- `Kpi({ label, value, unit })`.

- [ ] **Step 1 : test**

```tsx
// tests/carnet.test.tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";
const bet = { id: "b1", match_id: "m1", home_team: "Arsenal", away_team: "Chelsea", competition: "E0", kickoff_at: "2026-09-07T15:30:00Z", outcome: "home", bookmaker: "winamax_fr", odds: 2.05, stake: 40, status: "WON", payout: 82, created_at: "2026-09-06T10:00:00Z", settled_at: "2026-09-07T18:00:00Z" };
const summary = { stakes: 90, settled_stakes: 40, payouts: 82, profit: 42, roi: 1.05, pending: 1, settled: 1, by_bookmaker: {}, by_competition: {} };
describe("carnet", () => {
  it("KPI, liste, statut, suppression d'un pari en attente", async () => {
    let deleted = "";
    server.use(
      http.get(`${API}/api/v1/bankroll`, () => HttpResponse.json({ success: true, message: "", data: { items: [bet, { ...bet, id: "b2", status: "PENDING", payout: null, stake: 50 }], summary } })),
      http.delete(`${API}/api/v1/bankroll/b2`, () => { deleted = "b2"; return HttpResponse.json({ success: true, message: "", data: { id: "b2" } }); }),
      http.get(`${API}/api/v1/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [], pagination: { page: 1, limit: 200, total: 0 } } })),
    );
    const { Bankroll } = await import("@/components/Bankroll");
    render(<Bankroll token="tok" />);
    expect(await screen.findByText("Ton vrai bilan.")).toBeInTheDocument();
    expect(screen.getByText("90")).toBeInTheDocument();
    expect(screen.getByText("+42")).toBeInTheDocument();
    expect(screen.getByText("Gagné")).toBeInTheDocument();
    expect(screen.getByText("En attente")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Supprimer" }));
    await waitFor(() => expect(deleted).toBe("b2"));
  });
  it("saisie : envoie le pari et rafraîchit", async () => {
    let posted: unknown = null;
    server.use(
      http.get(`${API}/api/v1/bankroll`, () => HttpResponse.json({ success: true, message: "", data: { items: [], summary: { ...summary, stakes: 0, settled_stakes: 0, payouts: 0, profit: 0, roi: null, pending: 0, settled: 0 } } })),
      http.get(`${API}/api/v1/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [{ id: "m1", competition: "F1", league: "Ligue 1", home_team: "Lyon", away_team: "Marseille", kickoff_at: "2026-09-13T15:15:00Z", status: "SCHEDULED", favourite: null, reference: null, best_gap: null, movement: null, odds_taken_at: null, locked: false }], pagination: { page: 1, limit: 200, total: 1 } } })),
      http.post(`${API}/api/v1/bankroll`, async ({ request }) => { posted = await request.json(); return HttpResponse.json({ success: true, message: "", data: bet }, { status: 201 }); }),
    );
    const { Bankroll } = await import("@/components/Bankroll");
    render(<Bankroll token="tok" preselected="m1" />);
    expect(await screen.findByText("Aucun pari noté. Le premier est en bas de page.")).toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText("Cote"), { target: { value: "1.78" } });
    fireEvent.change(screen.getByLabelText("Mise"), { target: { value: "50" } });
    fireEvent.click(screen.getByRole("button", { name: "Noter ce pari" }));
    await waitFor(() => expect(posted).toMatchObject({ match_id: "m1", outcome: "home", bookmaker: "betclic_fr", odds: 1.78, stake: 50 }));
  });
});
```

- [ ] **Step 2 : code**

`components/Kpi.tsx` :
```tsx
export function Kpi({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return <div className="border-b border-line py-6 md:border-r md:pr-6 md:last:border-r-0"><div className="eyebrow">{label}</div><div className="mt-2 font-tight text-[44px] md:text-[56px] font-extrabold leading-none tracking-[-0.06em]">{value}{unit && <span className="ml-1 text-[22px] tracking-[-0.02em]">{unit}</span>}</div></div>;
}
```

`components/BetForm.tsx` :
```tsx
"use client";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { MatchSummary } from "@/lib/types";
import { BOOK_LABELS } from "@/lib/types";
import { formatDateFr } from "@/lib/format";
const label = "block text-[12px] font-semibold uppercase tracking-[0.04em] text-muted";
const field = "mt-2 w-full border-0 border-b border-ink bg-transparent py-2 text-[17px] font-medium outline-none";
export function BetForm({ token, preselected, onSaved }: { token: string; preselected?: string; onSaved: () => void }) {
  const [matches, setMatches] = useState<MatchSummary[]>([]);
  const [f, setF] = useState({ match_id: preselected ?? "", outcome: "home", bookmaker: "betclic_fr", odds: "", stake: "" });
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.matches({ limit: 200 }, token).then((r) => { setMatches(r.items); setF((s) => ({ ...s, match_id: s.match_id || r.items[0]?.id || "" })); }).catch(() => setMatches([])); }, [token]);
  const m = matches.find((x) => x.id === f.match_id);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    try {
      await api.bankroll.create(token, { match_id: f.match_id, outcome: f.outcome, bookmaker: f.bookmaker, odds: Number(f.odds), stake: Number(f.stake) });
      setF((s) => ({ ...s, odds: "", stake: "" })); onSaved();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Impossible d'enregistrer. Réessaie."); }
  }
  return (
    <form onSubmit={submit} className="mt-12 grid items-end gap-4 border-t border-ink pt-6 md:grid-cols-[2fr_1fr_1fr_1fr_1fr_auto]">
      <div><label className={label} htmlFor="match">Match</label><select id="match" className={field} value={f.match_id} onChange={(e) => setF({ ...f, match_id: e.target.value })}>{matches.map((x) => <option key={x.id} value={x.id}>{x.home_team} – {x.away_team} · {formatDateFr(x.kickoff_at)}</option>)}</select></div>
      <div><label className={label} htmlFor="outcome">Pari</label><select id="outcome" className={field} value={f.outcome} onChange={(e) => setF({ ...f, outcome: e.target.value })}><option value="home">{m?.home_team ?? "Domicile"}</option><option value="draw">Nul</option><option value="away">{m?.away_team ?? "Extérieur"}</option></select></div>
      <div><label className={label} htmlFor="bookmaker">Bookmaker</label><select id="bookmaker" className={field} value={f.bookmaker} onChange={(e) => setF({ ...f, bookmaker: e.target.value })}>{Object.entries(BOOK_LABELS).filter(([k]) => k !== "pinnacle").map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
      <div><label className={label} htmlFor="odds">Cote</label><input id="odds" type="number" step="0.01" min="1.01" required className={field} value={f.odds} onChange={(e) => setF({ ...f, odds: e.target.value })} /></div>
      <div><label className={label} htmlFor="stake">Mise</label><input id="stake" type="number" step="1" min="1" required className={field} value={f.stake} onChange={(e) => setF({ ...f, stake: e.target.value })} /></div>
      <button type="submit" className="btn" disabled={!f.match_id}>Noter ce pari</button>
      {error && <p role="alert" className="md:col-span-6 text-[14px] font-medium">{error}</p>}
    </form>
  );
}
```

`components/Bankroll.tsx` :
```tsx
"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BankrollSummary, Bet } from "@/lib/types";
import { BOOK_LABELS } from "@/lib/types";
import { formatDateFr, formatEuro, formatOdds, formatSigned } from "@/lib/format";
import { Kpi } from "./Kpi";
import { BetForm } from "./BetForm";
const STATUS: Record<Bet["status"], string> = { PENDING: "En attente", WON: "Gagné", LOST: "Perdu", VOID: "Annulé" };
export function Bankroll({ token, preselected }: { token: string; preselected?: string }) {
  const [data, setData] = useState<{ items: Bet[]; summary: BankrollSummary } | null>(null);
  const load = useCallback(() => api.bankroll.list(token).then(setData), [token]);
  useEffect(() => { load(); }, [load]);
  if (!data) return <p className="text-muted">Chargement…</p>;
  const s = data.summary;
  const outcomeLabel = (b: Bet) => (b.outcome === "home" ? b.home_team : b.outcome === "away" ? b.away_team : "Nul");
  return (
    <>
      <p className="eyebrow">Carnet</p>
      <h1 className="h-section mt-3">Ton vrai bilan.</h1>
      <p className="mt-3 mb-10 max-w-[56ch] text-[19px] text-muted">Chaque pari que tu notes est réglé automatiquement au résultat. Pas de conseil de mise, juste ce que tu as engagé et ce que ça a rendu.</p>
      <div className="grid border-t border-ink md:grid-cols-4">
        <Kpi label="Engagé" value={String(Math.round(s.stakes))} unit="€" />
        <Kpi label="Réglé" value={String(Math.round(s.settled_stakes))} unit="€" />
        <Kpi label="Résultat" value={s.settled_stakes ? formatSigned(Math.round(s.profit)).replace(",0", "") : "—"} unit={s.settled_stakes ? "€" : undefined} />
        <Kpi label="Rendement" value={s.roi === null ? "—" : formatSigned(s.roi * 100)} unit={s.roi === null ? undefined : "%"} />
      </div>
      {data.items.length === 0 ? <p className="hair mt-10 py-8 text-[19px]">Aucun pari noté. Le premier est en bas de page.</p> : (
        <table className="mt-12 w-full border-collapse text-[15px]">
          <thead><tr>{["Match", "Pari", "Bookmaker", "Cote", "Mise", "Gain", "Statut", ""].map((h, i) => <th key={h + i} className={`border-b border-ink pb-3 text-[12px] font-semibold uppercase tracking-[0.06em] text-muted ${i >= 3 ? "text-right" : "text-left"}`}>{h}</th>)}</tr></thead>
          <tbody>{data.items.map((b) => (
            <tr key={b.id}>
              <td className="border-b border-line py-4 font-semibold">{b.home_team} – {b.away_team}<span className="block text-[13px] font-normal text-muted">{formatDateFr(b.kickoff_at)}</span></td>
              <td className="border-b border-line py-4">{outcomeLabel(b)}</td>
              <td className="border-b border-line py-4">{BOOK_LABELS[b.bookmaker] ?? b.bookmaker}</td>
              <td className="border-b border-line py-4 text-right tabular-nums">{formatOdds(b.odds)}</td>
              <td className="border-b border-line py-4 text-right tabular-nums">{formatEuro(b.stake)}</td>
              <td className="border-b border-line py-4 text-right tabular-nums">{b.payout === null ? "—" : formatEuro(b.payout)}</td>
              <td className={`border-b border-line py-4 text-right text-[12px] font-semibold uppercase tracking-[0.04em] ${b.status === "PENDING" ? "text-link" : b.status === "WON" ? "text-ink" : "text-faint"}`}>{STATUS[b.status]}</td>
              <td className="border-b border-line py-4 text-right">{b.status === "PENDING" && <button className="text-[13px] font-medium text-link" onClick={() => api.bankroll.remove(token, b.id).then(load)}>Supprimer</button>}</td>
            </tr>
          ))}</tbody>
        </table>
      )}
      <BetForm token={token} preselected={preselected} onSaved={load} />
    </>
  );
}
```

Le test attend `"+42"` pour le résultat : `formatSigned(42)` donne `"+42,0"`, d'où le `.replace(",0", "")` ; plus propre : ajouter `formatSignedInt` dans `lib/format.ts` (`${x >= 0 ? "+" : "−"}${Math.abs(Math.round(x))}`) et l'utiliser pour Résultat. Faire ça.

`app/carnet/page.tsx` :
```tsx
import { redirect } from "next/navigation";
import { getToken, getUser } from "@/lib/session";
import { Bankroll } from "@/components/Bankroll";
export const dynamic = "force-dynamic";
export default async function Carnet({ searchParams }: { searchParams: Promise<{ match?: string }> }) {
  const [token, user, { match }] = [await getToken(), await getUser(), await searchParams];
  if (!token || !user) redirect("/connexion");
  return <section className="bg-grey"><div className="site py-14 md:py-20"><Bankroll token={token} preselected={match} /></div></section>;
}
```

- [ ] **Step 3 : lancer, build, commit**

```bash
git add -A && git commit -m "feat(front): carnet de bankroll — KPI, liste réglée, saisie, suppression"
```

---

### Task 9 : Track record et pages légales

**Files:**
- Create: `app/track-record/page.tsx`, `app/mentions-legales/page.tsx`, `app/cgu/page.tsx`
- Test: `tests/pages.track.test.tsx`

**Interfaces:**
- `/track-record?competition=F1` : serveur, fond noir ; `api.trackRecord()` (toutes) ; chiffre 200 px de la compétition sélectionnée (F1 par défaut, sinon la première), phrase de provenance (« le favori affiché est celui du dernier relevé avant le coup d'envoi, jamais recalculé après coup »), tableau (Compétition / Matchs / Favori gagnant / Taux), lignes cliquables (`?competition=`).
- Pages légales : gabarit statique avec les rubriques (éditeur, hébergeur, données, ANJ) et un encadré « Texte à compléter par Lucas » ; `robots` noindex tant que le texte n'est pas final.

- [ ] **Step 1 : test**

```tsx
// tests/pages.track.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => undefined }) }));
describe("track record", () => {
  it("chiffre de la compétition choisie et tableau", async () => {
    server.use(http.get(`${API}/api/v1/track-record`, () => HttpResponse.json({ success: true, message: "", data: { note: "Le favori gagne environ une fois sur deux : c'est le marché, pas nous.", items: [{ competition: "E0", played: 80, favourite_won: 41, favourite_rate: 0.512 }, { competition: "F1", played: 72, favourite_won: 39, favourite_rate: 0.542 }] } })));
    const Page = (await import("@/app/track-record/page")).default;
    render(await Page({ searchParams: Promise.resolve({ competition: "F1" }) }));
    expect(screen.getByText("54")).toBeInTheDocument();
    expect(screen.getByText(/des favoris ont gagné en Ligue 1/)).toBeInTheDocument();
    expect(screen.getByText("Premier League")).toBeInTheDocument();
    expect(screen.getByText("51 %")).toBeInTheDocument();
  });
  it("vide : phrase d'attente", async () => {
    server.use(http.get(`${API}/api/v1/track-record`, () => HttpResponse.json({ success: true, message: "", data: { note: "n", items: [] } })));
    const Page = (await import("@/app/track-record/page")).default;
    render(await Page({ searchParams: Promise.resolve({}) }));
    expect(screen.getByText("Pas encore de match terminé avec un relevé de cotes. Le track record commence au premier coup d'envoi.")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2 : code**

`app/track-record/page.tsx` :
```tsx
import Link from "next/link";
import { api } from "@/lib/api";
import { COMPETITIONS } from "@/lib/types";
import { BigNumber } from "@/components/BigNumber";
export const revalidate = 300;
export default async function TrackRecord({ searchParams }: { searchParams: Promise<{ competition?: string }> }) {
  const { competition } = await searchParams;
  const { items, note } = await api.trackRecord();
  const sel = items.find((r) => r.competition === (competition ?? "F1")) ?? items[0] ?? null;
  return (
    <section className="bg-black text-paper">
      <div className="site py-16 md:py-24">
        <p className="eyebrow text-faint">Track record · public</p>
        {sel === null ? <p className="hair-dark mt-8 py-8 text-[19px]">Pas encore de match terminé avec un relevé de cotes. Le track record commence au premier coup d'envoi.</p> : (
          <div className="mt-4 grid gap-12 md:grid-cols-2 md:gap-16">
            <div>
              <div className="num-page"><BigNumber value={Math.round(sel.favourite_rate * 100)} suffix="%" /></div>
              <p className="mt-6 max-w-[40ch] text-[19px] leading-relaxed text-faint">des favoris ont gagné en {COMPETITIONS[sel.competition] ?? sel.competition} cette saison, sur {sel.played} matchs. {note} Le favori affiché est celui du dernier relevé avant le coup d'envoi, jamais recalculé après coup.</p>
            </div>
            <table className="w-full border-collapse text-[16px]">
              <thead><tr>{["Compétition", "Matchs", "Favori gagnant", "Taux"].map((h, i) => <th key={h} className={`border-b border-paper pb-3 text-[12px] font-semibold uppercase tracking-[0.06em] text-faint ${i ? "text-right" : "text-left"}`}>{h}</th>)}</tr></thead>
              <tbody>{items.map((r) => (
                <tr key={r.competition} className={r.competition === sel.competition ? "font-bold" : ""}>
                  <td className="border-b border-line-dark py-4"><Link href={`/track-record?competition=${r.competition}`}>{COMPETITIONS[r.competition] ?? r.competition}</Link></td>
                  <td className="border-b border-line-dark py-4 text-right tabular-nums">{r.played}</td>
                  <td className="border-b border-line-dark py-4 text-right tabular-nums">{r.favourite_won}</td>
                  <td className="border-b border-line-dark py-4 text-right tabular-nums">{Math.round(r.favourite_rate * 100)} %</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
```

`app/mentions-legales/page.tsx` et `app/cgu/page.tsx` : même gabarit —
```tsx
export const metadata = { robots: { index: false } };
export default function MentionsLegales() {
  return (
    <section className="site py-16 md:py-24 max-w-[760px]">
      <h1 className="h-section">Mentions légales.</h1>
      <p className="hair mt-8 py-5 text-[15px] text-muted">Texte à compléter par Lucas avant la mise en ligne.</p>
      {["Éditeur", "Hébergeur", "Données personnelles", "Jeu responsable"].map((t) => <div key={t} className="hair py-6"><h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">{t}</h2><p className="mt-2 text-[16px] text-muted">À compléter.</p></div>)}
    </section>
  );
}
```
(pour `cgu` : titre « Conditions d'utilisation. », rubriques « Objet », « Compte », « Abonnement », « Responsabilité »).

- [ ] **Step 3 : lancer, build, commit**

```bash
git add -A && git commit -m "feat(front): track record public par compétition, gabarits des pages légales"
```

---

### Task 10 : Finitions — états, mobile, accessibilité, performance, CI, README

**Files:**
- Create: `app/not-found.tsx`, `app/error.tsx`, `app/loading.tsx`, `app/matchs/loading.tsx`, `app/matchs/[id]/loading.tsx`, `frontend/README.md`
- Modify: `.github/workflows/quality-checks.yml` (job `frontend-lint` → `frontend-checks` : `npm ci`, `npm run lint`, `npm test`, `npm run build`), `next.config.mjs` (images non optimisées par Next pour les WebP locaux : `images: { unoptimized: true }` si `next/image` n'est pas utilisé — on utilise `<img>`/`<picture>`, donc rien à changer ; retirer le fichier s'il est vide de config utile, sinon le laisser)
- Test: `tests/a11y.test.tsx`

**Interfaces:**
- `not-found.tsx` : « Cette page n'existe pas. » + lien « Voir les matchs › ».
- `error.tsx` (client) : « Le service ne répond pas. Réessaie dans un instant. » + bouton « Réessayer » (`reset()`).
- `loading.tsx` : squelettes gris (barres `bg-grey` animées `animate-pulse`) reprenant la structure de la page (titre, 4 lignes).
- `tests/a11y.test.tsx` : chaque page publique rendue avec des données MSW a exactement un `h1`, chaque `img` a un attribut `alt`, chaque `table` a des `th`, et le bandeau ANJ (« 09 74 75 13 13 ») est présent dans le `Footer`.

- [ ] **Step 1 : test a11y**

```tsx
// tests/a11y.test.tsx
import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => undefined }) }));
const empty = () => HttpResponse.json({ success: true, message: "", data: { items: [], pagination: { page: 1, limit: 50, total: 0 }, note: "n" } });
describe("accessibilité de base", () => {
  it("un seul h1 par page, alt sur les images, en-têtes de tableau", async () => {
    server.use(http.get(`${API}/api/v1/matches`, empty), http.get(`${API}/api/v1/track-record`, empty));
    for (const mod of ["@/app/page", "@/app/matchs/page", "@/app/track-record/page", "@/app/tarifs/page"]) {
      const Page = (await import(mod)).default;
      const { container, unmount } = render(await Page({ searchParams: Promise.resolve({}) }));
      expect(container.querySelectorAll("h1").length, mod).toBe(1);
      container.querySelectorAll("img").forEach((img) => expect(img.hasAttribute("alt"), mod).toBe(true));
      container.querySelectorAll("table").forEach((t) => expect(t.querySelectorAll("th").length, mod).toBeGreaterThan(0));
      unmount();
    }
  });
  it("le pied de page porte le numéro d'aide", async () => {
    const { Footer } = await import("@/components/Footer");
    const { container } = render(await Footer());
    expect(container.textContent).toContain("09 74 75 13 13");
  });
});
```

- [ ] **Step 2 : fichiers**

`app/not-found.tsx` :
```tsx
import Link from "next/link";
export default function NotFound() {
  return <section className="site py-24"><h1 className="h-section">Cette page n'existe pas.</h1><Link href="/matchs" className="link mt-6 inline-block text-[17px]">Voir les matchs ›</Link></section>;
}
```

`app/error.tsx` :
```tsx
"use client";
export default function Error({ reset }: { error: Error; reset: () => void }) {
  return <section className="site py-24"><h1 className="h-section">Le service ne répond pas.</h1><p className="mt-3 text-[19px] text-muted">Réessaie dans un instant.</p><button onClick={reset} className="btn mt-8">Réessayer</button></section>;
}
```

`app/loading.tsx` (et copies dans `matchs/`, `matchs/[id]/`) :
```tsx
export default function Loading() {
  return <section className="site py-20 animate-pulse"><div className="h-12 w-64 bg-grey" />{[0, 1, 2, 3].map((i) => <div key={i} className="mt-6 h-16 border-t border-line bg-grey/60" />)}</section>;
}
```

`.github/workflows/quality-checks.yml`, job front :
```yaml
  frontend-checks:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: frontend } }
    env: { NEXT_PUBLIC_API_URL: http://localhost:8000 }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "22", cache: "npm", cache-dependency-path: "frontend/package-lock.json" }
      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build
```

`frontend/README.md` : lancement (`npm install`, `.env.local` avec `NEXT_PUBLIC_API_URL`, `npm run dev`), tests, build, structure des dossiers, les jetons, la règle « aucune couleur hors jetons », les photos (crédits, à remplacer), et la procédure de déploiement : service Next dans Coolify (Dockerfile ci-dessous) à côté de l'API.

`frontend/Dockerfile` :
```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```
et dans `next.config.mjs` : `const nextConfig = { output: "standalone" };`. Ajouter à `deploy/coolify.md` une étape 9 : service `front` depuis `frontend/Dockerfile` avec l'argument de build `NEXT_PUBLIC_API_URL=https://<domaine de l'API>`, domaine du site pointé dessus.

- [ ] **Step 3 : vérification mobile et performance**

Avec `npm run dev` et le backend : ouvrir l'accueil, la liste, un match, le carnet en largeur 390 px (outils de développement) ; corriger tout débordement horizontal ; vérifier le focus clavier visible sur les liens et boutons ; vérifier `prefers-reduced-motion` (les chiffres s'affichent sans compte). Lancer Lighthouse (Chrome, mobile) sur l'accueil : accessibilité ≥ 90, performance ≥ 90 ; si la performance est en dessous, réduire la photo du héros (1600 px, q 65) et vérifier que `fetchPriority="high"` est bien posé.

- [ ] **Step 4 : suite complète et commit**

Run : `npm run lint && npm test && npm run build` → verts. `grep -rniE "prédiction|pronostic|value bet|confiance|prediction|confidence" app components lib` → vide.
```bash
git add -A && git commit -m "feat(front): états vides/erreur/chargement, accessibilité, Dockerfile standalone, CI front, README"
```

---

## Self-review du plan

- **Couverture du spec** : §2 système visuel (Task 1 jetons + utilitaires, Task 2 composants, photos Task 3, mouvement `BigNumber`/`Reveal`, voix dans les textes de chaque page) ; §3 neuf écrans (Task 3 accueil, 4 liste, 5 match, 7 bookmakers et tarifs, 8 carnet, 9 track record et légal, 6 compte/connexion/inscription) ; §4 architecture (client API Task 1, session cookie Task 6, rendu serveur avec `revalidate`, composants un fichier chacun, états Task 10, accessibilité Tasks 1 et 10) ; §5 tests (Vitest + MSW dans chaque tâche, build en CI Task 10, Lighthouse Task 10) ; §6 hors périmètre respecté (pas de LLM, pas de mobile natif, pas de paiement : bouton « S'abonner » mène à un message d'attente, décision assumée).
- **Placeholders** : aucun ; les pages légales sont volontairement des gabarits « à compléter par Lucas », avec `noindex`.
- **Cohérence des noms** : `api.*` (Task 1) utilisé à l'identique dans 3-9 ; `getToken`/`getUser`/`isPro` (Task 2) dans 3-9 ; `MatchSummary`/`MatchDetail`/`Bet`/`BookRow`/`TrackRow` (Task 1) partout ; `Reserved` (Task 2) dans 5 et 7 ; `BigNumber` dans 3, 5, 9 ; `formatSignedInt` ajouté en Task 8.
- **Déviations du spec** : Next.js 16 au lieu de 15 (version déjà installée) ; le paiement n'existant pas côté API, « S'abonner » affiche un message d'attente ; le jeton est passé au composant client `Bankroll` en prop depuis le serveur (le cookie est `httpOnly`).
