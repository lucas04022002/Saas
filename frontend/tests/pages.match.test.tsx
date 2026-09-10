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
