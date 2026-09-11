import type { BankrollSummary, Bet, BookRow, Legal, MatchDetail, MatchSummary, Pagination, TrackRow, User } from "./types";

import { parseEnvelope } from "./envelope";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Réexportés depuis leur module d'origine : de nombreux composants importent encore `ApiError` (et
// `parseEnvelope`) depuis `@/lib/api`, et c'est la porte d'entrée naturelle côté serveur.
export { ApiError, parseEnvelope } from "./envelope";

async function call<T>(path: string, init: RequestInit & { token?: string; revalidate?: number } = {}): Promise<T> {
  const { token, revalidate, ...rest } = init;
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(rest.headers as Record<string, string>) };
  if (token) headers.Authorization = `Bearer ${token}`;
  // Une réponse authentifiée (jeton présent) est personnalisée (abonnement, carnet...) : elle ne doit
  // jamais rejoindre le cache de données partagé de Next.js, où elle pourrait fuiter vers un autre
  // visiteur. `cache: "no-store"` prime alors sur tout `revalidate` demandé par l'appelant.
  const cacheInit: RequestInit = token ? { cache: "no-store" } : revalidate !== undefined ? ({ next: { revalidate } } as RequestInit) : {};
  const res = await fetch(`${BASE}${path}`, { ...rest, ...cacheInit, headers });
  return parseEnvelope<T>(res);
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
  me: (token: string) => call<User>("/api/v1/auth/me", { token }),
  bankroll: {
    list: (token: string) => call<{ items: Bet[]; summary: BankrollSummary }>("/api/v1/bankroll", { token }),
    create: (token: string, p: { match_id: string; outcome: string; bookmaker: string; odds: number; stake: number }) =>
      call<Bet>("/api/v1/bankroll", { method: "POST", token, body: JSON.stringify(p) }),
    remove: (token: string, id: string) => call<{ id: string }>(`/api/v1/bankroll/${id}`, { method: "DELETE", token }),
    void: (token: string, id: string) => call<Bet>(`/api/v1/bankroll/${id}/void`, { method: "POST", token }),
  },
};
