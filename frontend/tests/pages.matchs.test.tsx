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
  it("sous-titre : compte les matchs groupés, pas items.length (une compétition hors ORDER ne compte pas)", async () => {
    server.use(http.get(`${API}/api/v1/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [m("1", "E0", "Premier League", "Arsenal", "Chelsea"), m("2", "XX", "Ligue inconnue", "A", "B")], pagination: { page: 1, limit: 200, total: 2 } } })));
    const Page = (await import("@/app/matchs/page")).default;
    render(await Page({ searchParams: Promise.resolve({ date: "2026-09-13", competition: undefined }) }));
    expect(screen.getByText(/1 match · relevé de/)).toBeInTheDocument();
  });
  it("vide : phrase d'invitation", async () => {
    server.use(http.get(`${API}/api/v1/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [], pagination: { page: 1, limit: 200, total: 0 } } })));
    const Page = (await import("@/app/matchs/page")).default;
    render(await Page({ searchParams: Promise.resolve({ date: "2026-09-13", competition: "CL" }) }));
    expect(screen.getByText("Aucun match ce jour-là pour cette compétition.")).toBeInTheDocument();
  });
});
