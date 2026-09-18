import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";

vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => ({ value: "tok" }) }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }) }));

function connecte(plan: string) {
  server.use(
    http.get(`${API}/api/v1/auth/me`, () =>
      HttpResponse.json({ success: true, message: "", data: { id: "u1", first_name: "corlaine", email: "c@t.fr", role: "USER", subscription_plan: plan } })),
  );
}

async function rendre() {
  const { Nav } = await import("@/components/Nav");
  render(await Nav());
}

const lien = (nom: string | RegExp) => screen.getByRole("link", { name: nom }).getAttribute("href");

describe("barre de navigation", () => {
  it("abonné : le prénom mène au compte, pas au carnet", async () => {
    // Le défaut réel : /compte n'avait qu'un seul point d'entrée, et il basculait
    // vers /carnet dès qu'on payait. La page où l'on résilie devenait donc
    // inatteignable au moment précis où l'on commençait à payer.
    connecte("PRO");
    await rendre();

    expect(lien("corlaine")).toBe("/compte");
  });

  it("abonné : le carnet reste accessible, comme lien à part entière", async () => {
    connecte("PRO");
    await rendre();

    expect(lien("Carnet")).toBe("/carnet");
  });

  it("compte gratuit : le prénom mène au compte, et pas de lien Carnet", async () => {
    connecte("STARTER");
    await rendre();

    expect(lien("corlaine")).toBe("/compte");
    expect(screen.queryByRole("link", { name: "Carnet" })).not.toBeInTheDocument();
  });

  it("visiteur : « Se connecter », et rien à déconnecter", async () => {
    server.use(http.get(`${API}/api/v1/auth/me`, () => HttpResponse.json({ detail: "non" }, { status: 401 })));
    await rendre();

    expect(lien("Se connecter")).toBe("/connexion");
    expect(screen.queryByRole("button", { name: "Se déconnecter" })).not.toBeInTheDocument();
  });

  it("connecté : le bouton de déconnexion est dans la barre", async () => {
    connecte("PRO");
    await rendre();

    expect(screen.getByRole("button", { name: "Se déconnecter" })).toBeInTheDocument();
  });
});
