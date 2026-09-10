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
