import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => undefined }) }));
const m = (id: string, competition: string, league: string, home: string, away: string) => ({ id, competition, league, home_team: home, away_team: away, kickoff_at: "2026-09-13T15:15:00Z", status: "SCHEDULED",
  favourite: { outcome: "home", label: home, prob: 0.55, source: "pinnacle" }, reference: { home: 0.55, draw: 0.25, away: 0.2 }, best_gap: null, movement: null, odds_taken_at: "2026-09-13T10:00:00Z", locked: true,
  top_score: { score: "1-0", probability: 0.13 } });
describe("liste des matchs", () => {
  it("groupe par compétition et affiche le sous-titre", async () => {
    let query = "";
    server.use(http.get(`${API}/api/v1/matches`, ({ request }) => { query = new URL(request.url).search; return HttpResponse.json({ success: true, message: "", data: { items: [m("1", "E0", "Premier League", "Arsenal", "Chelsea"), m("2", "F1", "Ligue 1", "Lyon", "Marseille")], pagination: { page: 1, limit: 200, total: 2 }, quota: { plan: "ANONYMOUS", limit: 0, used: 0, remaining: 0, resets_at: null } } }); }));
    const Page = (await import("@/app/matchs/page")).default;
    render(await Page({ searchParams: Promise.resolve({ date: "2026-09-13", competition: undefined }) }));
    expect(query).toContain("date=2026-09-13");
    expect(screen.getByText("Matchs.")).toBeInTheDocument();
    expect(screen.getByText(/2 matchs · relevé de/)).toBeInTheDocument();
    const headings = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(headings).toEqual(["Ligue 1", "Premier League"]);
  });
  it("sous-titre : compte les matchs groupés, pas items.length (une compétition hors ORDER ne compte pas)", async () => {
    server.use(http.get(`${API}/api/v1/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [m("1", "E0", "Premier League", "Arsenal", "Chelsea"), m("2", "XX", "Ligue inconnue", "A", "B")], pagination: { page: 1, limit: 200, total: 2 }, quota: { plan: "ANONYMOUS", limit: 0, used: 0, remaining: 0, resets_at: null } } })));
    const Page = (await import("@/app/matchs/page")).default;
    render(await Page({ searchParams: Promise.resolve({ date: "2026-09-13", competition: undefined }) }));
    expect(screen.getByText(/1 match · relevé de/)).toBeInTheDocument();
  });
  it("vide : phrase d'invitation", async () => {
    server.use(http.get(`${API}/api/v1/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [], pagination: { page: 1, limit: 200, total: 0 }, quota: { plan: "ANONYMOUS", limit: 0, used: 0, remaining: 0, resets_at: null } } })));
    const Page = (await import("@/app/matchs/page")).default;
    render(await Page({ searchParams: Promise.resolve({ date: "2026-09-13", competition: "CL" }) }));
    expect(screen.getByText("Aucun match ce jour-là pour cette compétition.")).toBeInTheDocument();
  });
});

// ---- un jour vide annonce les prochains matchs (22/09/2026, trêve internationale) ----

const VIDE = { success: true, message: "", data: { items: [], pagination: { page: 1, limit: 200, total: 0 }, quota: { plan: "ANONYMOUS", limit: 0, used: 0, remaining: 0, resets_at: null } } };

describe("jour sans match", () => {
  it("annonce le prochain jour avec des matchs, avec le lien", async () => {
    server.use(
      http.get(`${API}/api/v1/matches`, () => HttpResponse.json(VIDE)),
      http.get(`${API}/api/v1/matches/next`, () => HttpResponse.json({ success: true, message: "", data: { date: "2026-09-24", count: 12, competitions: ["NL"] } })),
    );
    const Page = (await import("@/app/matchs/page")).default;
    render(await Page({ searchParams: Promise.resolve({ date: "2026-09-22", competition: undefined }) }));
    const lien = screen.getByRole("link", { name: /Prochains matchs/ });
    expect(lien).toHaveAttribute("href", "/matchs?date=2026-09-24");
    expect(lien.textContent).toMatch(/jeudi 24 septembre/);
    // « Ligue des Nations » existe aussi dans la pastille du filtre : on lit le paragraphe des prochains matchs.
    expect(screen.getByText(/12 matchs/).textContent).toMatch(/Ligue des Nations/);
  });

  it("le lien garde le filtre de compétition", async () => {
    let question = "";
    server.use(
      http.get(`${API}/api/v1/matches`, () => HttpResponse.json(VIDE)),
      http.get(`${API}/api/v1/matches/next`, ({ request }) => { question = new URL(request.url).search; return HttpResponse.json({ success: true, message: "", data: { date: "2026-10-13", count: 18, competitions: ["CL"] } }); }),
    );
    const Page = (await import("@/app/matchs/page")).default;
    render(await Page({ searchParams: Promise.resolve({ date: "2026-09-22", competition: "CL" }) }));
    expect(question).toContain("competition=CL");
    expect(screen.getByRole("link", { name: /Prochains matchs/ })).toHaveAttribute("href", "/matchs?date=2026-10-13&competition=CL");
  });

  it("rien devant : le message reste sobre, sans lien cassé", async () => {
    server.use(
      http.get(`${API}/api/v1/matches`, () => HttpResponse.json(VIDE)),
      http.get(`${API}/api/v1/matches/next`, () => HttpResponse.json({ success: true, message: "", data: null })),
    );
    const Page = (await import("@/app/matchs/page")).default;
    render(await Page({ searchParams: Promise.resolve({ date: "2026-09-22", competition: undefined }) }));
    expect(screen.getByText(/Aucun match ce jour-là/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Prochains matchs/ })).not.toBeInTheDocument();
  });
});
