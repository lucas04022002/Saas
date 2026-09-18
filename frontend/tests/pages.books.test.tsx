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

describe("tarifs", () => {
  it("le prix affiché est celui de Stripe, pas une constante", async () => {
    // Le défaut corrigé : le prix était écrit en dur dans la page. Un tarif
    // passé à 12,50 € chez Stripe aurait laissé le site annoncer 9 €, et
    // l'écart ne se serait vu que sur le relevé d'un client.
    server.use(
      http.get(`${API}/api/v1/auth/me`, () => HttpResponse.json({ detail: "non" }, { status: 401 })),
      http.get(`${API}/api/v1/billing/plan`, () =>
        HttpResponse.json({ success: true, message: "", data: { amount_cents: 1250, currency: "EUR", interval: "month", interval_count: 1, livemode: true } })),
    );
    const Page = (await import("@/app/tarifs/page")).default;
    render(await Page());
    expect(screen.getByText("12,50")).toBeInTheDocument();
    expect(screen.queryByText("9")).not.toBeInTheDocument();
  });

  it("Stripe injoignable : la page affiche le repli plutôt qu'un trou", async () => {
    server.use(
      http.get(`${API}/api/v1/auth/me`, () => HttpResponse.json({ detail: "non" }, { status: 401 })),
      http.get(`${API}/api/v1/billing/plan`, () => HttpResponse.json({ detail: "boom" }, { status: 500 })),
    );
    const Page = (await import("@/app/tarifs/page")).default;
    render(await Page());
    expect(screen.getByText("9")).toBeInTheDocument();
  });

  it("tarifs : un abonné ne voit « Ton offre actuelle » qu'une fois", async () => {
    server.use(
      http.get(`${API}/api/v1/auth/me`, () => HttpResponse.json({ success: true, message: "", data: { id: "u", first_name: "L", email: "l@t.fr", role: "USER", subscription_plan: "PRO" } })),
    );
    const Page = (await import("@/app/tarifs/page")).default;
    render(await Page());
    expect(screen.getAllByText(/Ton offre actuelle/)).toHaveLength(1);
    expect(screen.getByText("Inclus dans ton offre.")).toBeInTheDocument();
    // Le badge était un cul-de-sac : un abonné venu revoir ce qu'il paie
    // n'avait, depuis cette page, aucun chemin vers l'endroit où l'on résilie.
    expect(screen.getByRole("link", { name: /Résilier/ }).getAttribute("href")).toBe("/compte");
  });
});
