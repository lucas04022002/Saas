import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";

vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => undefined }) }));

const match = { id: "m1", competition: "F1", league: "Ligue 1", home_team: "Lyon", away_team: "Marseille", kickoff_at: "2026-09-13T15:15:00Z", status: "SCHEDULED",
  favourite: { outcome: "home", label: "Lyon", prob: 0.58, source: "pinnacle" }, reference: { home: 0.58, draw: 0.24, away: 0.18 }, best_gap: null, movement: null, odds_taken_at: "2026-09-13T10:00:00Z", locked: true,
  top_score: { score: "2-1", probability: 0.12 } };

describe("accueil", () => {
  it("héros avec le match phare et quatre lignes", async () => {
    server.use(
      http.get(`${API}/api/v1/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [match, { ...match, id: "m2", home_team: "Lens", away_team: "Lille" }], pagination: { page: 1, limit: 50, total: 2 }, quota: { plan: "ANONYMOUS", limit: 0, used: 0, remaining: 0, resets_at: null } } })),
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
      http.get(`${API}/api/v1/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [], pagination: { page: 1, limit: 50, total: 0 }, quota: { plan: "ANONYMOUS", limit: 0, used: 0, remaining: 0, resets_at: null } } })),
      http.get(`${API}/api/v1/track-record`, () => HttpResponse.json({ success: true, message: "", data: { items: [], note: "n" } })),
    );
    const Page = (await import("@/app/page")).default;
    render(await Page());
    expect(screen.getByText("On ne prédit rien. On lit le marché.")).toBeInTheDocument();
    expect(screen.getByText("Aucun match aujourd'hui. Reviens demain.")).toBeInTheDocument();
  });
});
