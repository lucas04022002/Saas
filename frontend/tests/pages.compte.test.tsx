import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";

vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => ({ value: "tok" }) }) }));
// La page rend aussi `LogoutButton`, qui appelle `useRouter` : le mock doit
// porter les deux, sinon le rendu casse pour une raison sans rapport.
vi.mock("next/navigation", () => ({
  redirect: () => { throw new Error("redirigé"); },
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

const DANS_12_JOURS = new Date(Date.now() + 12 * 864e5).toISOString();

function compte(plan: string, abonnement: unknown) {
  server.use(
    http.get(`${API}/api/v1/auth/me`, () =>
      HttpResponse.json({ success: true, message: "", data: { id: "u1", first_name: "Lucas", email: "l@t.fr", role: "USER", subscription_plan: plan } })),
    http.get(`${API}/api/v1/billing/abonnement`, () =>
      HttpResponse.json({ success: true, message: "", data: abonnement })),
  );
}

async function rendre() {
  const Page = (await import("@/app/compte/page")).default;
  render(await Page({ searchParams: Promise.resolve({}) }));
}

describe("page Compte : se désabonner", () => {
  it("le bouton nomme la résiliation, pas seulement « gérer »", async () => {
    // Quelqu'un qui cherche à partir ne clique pas sur un bouton qui ne le dit pas.
    compte("PRO", { plan: "PRO", status: "ACTIVE", cancel_at_period_end: false, current_period_end: DANS_12_JOURS });
    await rendre();

    expect(screen.getByRole("button", { name: /Résilier/ })).toBeInTheDocument();
  });

  it("abonné actif : la date de fin de période est annoncée", async () => {
    compte("PRO", { plan: "PRO", status: "ACTIVE", cancel_at_period_end: false, current_period_end: DANS_12_JOURS });
    await rendre();

    expect(screen.getByText(/soit le /)).toBeInTheDocument();
  });

  it("après résiliation : la page le dit, alors que le plan est toujours PRO", async () => {
    // Le point dur. `cancel_at_period_end` porte l'information, pas le plan :
    // une page qui ne lit que le plan affiche exactement ce qu'elle affichait
    // avant, et l'utilisateur ne sait pas si sa demande a abouti.
    compte("PRO", { plan: "PRO", status: "ACTIVE", cancel_at_period_end: true, current_period_end: DANS_12_JOURS });
    await rendre();

    expect(screen.getByText(/Résiliation enregistrée/)).toBeInTheDocument();
    expect(screen.getByText(/ne serez pas prélevé/)).toBeInTheDocument();
  });

  it("l'API d'abonnement en panne n'emporte pas la page", async () => {
    server.use(
      http.get(`${API}/api/v1/auth/me`, () =>
        HttpResponse.json({ success: true, message: "", data: { id: "u1", first_name: "Lucas", email: "l@t.fr", role: "USER", subscription_plan: "PRO" } })),
      http.get(`${API}/api/v1/billing/abonnement`, () => HttpResponse.json({ detail: "boom" }, { status: 500 })),
    );
    await rendre();

    expect(screen.getByRole("button", { name: /Résilier/ })).toBeInTheDocument();
  });

  it("non abonné : c'est le bouton d'abonnement qui s'affiche", async () => {
    compte("STARTER", null);
    await rendre();

    expect(screen.getByRole("button", { name: /S'abonner/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Résilier/ })).not.toBeInTheDocument();
  });
});
