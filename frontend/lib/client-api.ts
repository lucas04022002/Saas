import { parseEnvelope } from "./api";
import type { BankrollSummary, Bet, MatchSummary, Pagination } from "./types";

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...init,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(init.headers as Record<string, string>) },
  });
  return parseEnvelope<T>(res);
}

export const clientApi = {
  bankroll: {
    list: () => call<{ items: Bet[]; summary: BankrollSummary }>("/api/bankroll"),
    create: (p: { match_id: string; outcome: string; bookmaker: string; odds: number; stake: number }) =>
      call<Bet>("/api/bankroll", { method: "POST", body: JSON.stringify(p) }),
    remove: (id: string) => call<{ id: string }>(`/api/bankroll/${id}`, { method: "DELETE" }),
    void: (id: string) => call<Bet>(`/api/bankroll/${id}/void`, { method: "POST" }),
  },
  matches: () => call<{ items: MatchSummary[]; pagination: Pagination }>("/api/matches"),
};
