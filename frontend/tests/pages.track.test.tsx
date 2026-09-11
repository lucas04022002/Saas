import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => undefined }) }));
describe("track record", () => {
  it("chiffre de la compétition choisie et tableau", async () => {
    server.use(http.get(`${API}/api/v1/track-record`, () => HttpResponse.json({ success: true, message: "", data: {
      note: "Le favori gagne environ une fois sur deux : c'est le marché, pas nous.",
      items: [{ competition: "E0", played: 80, favourite_won: 41, favourite_rate: 0.512 }, { competition: "F1", played: 72, favourite_won: 39, favourite_rate: 0.542 }],
      n_scored: 152, exact_score_rate: 0.111, winner_rate_from_score: 0.534, score_note: "Le marché touche le score exact environ une fois sur neuf.",
    } })));
    const Page = (await import("@/app/track-record/page")).default;
    render(await Page({ searchParams: Promise.resolve({ competition: "F1" }) }));
    expect(screen.getByText("54")).toBeInTheDocument();
    expect(screen.getByText(/des favoris ont gagné en Ligue 1/)).toBeInTheDocument();
    expect(screen.getByText("Premier League")).toBeInTheDocument();
    // Testing Library normalise tout blanc en espace ASCII avant comparaison : `getByText` retrouve la
    // cellule, mais seul le textContent brut prouve l'espace insécable exigé par la typographie française.
    expect(screen.getByText("51 %").textContent).toBe("51 %");
    // scores exacts / bons vainqueurs à partir du score affiché : deux KPI supplémentaires, sous la table
    expect(screen.getByText("Scores exacts touchés")).toBeInTheDocument();
    expect(screen.getByText("11")).toBeInTheDocument();
    expect(screen.getByText("Bons vainqueurs (score affiché)")).toBeInTheDocument();
    expect(screen.getByText("53")).toBeInTheDocument();
    expect(screen.getByText(/score exact environ une fois sur neuf/)).toBeInTheDocument();
  });
  it("vide : phrase d'attente, pas de KPI score sans mesure", async () => {
    server.use(http.get(`${API}/api/v1/track-record`, () => HttpResponse.json({ success: true, message: "", data: { note: "n", items: [], n_scored: 0, exact_score_rate: null, winner_rate_from_score: null, score_note: "s" } })));
    const Page = (await import("@/app/track-record/page")).default;
    render(await Page({ searchParams: Promise.resolve({}) }));
    expect(screen.getByText("Pas encore de match terminé avec un relevé de cotes. Le track record commence au premier coup d'envoi.")).toBeInTheDocument();
    expect(screen.queryByText("Scores exacts touchés")).not.toBeInTheDocument();
  });
});
