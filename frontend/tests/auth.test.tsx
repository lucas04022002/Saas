import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, refresh: vi.fn() }) }));
vi.mock("@/lib/client-session", () => ({ saveSession: vi.fn(async () => {}), clearSession: vi.fn(async () => {}) }));

describe("AuthForm", () => {
  it("connexion : appelle l'API, sauvegarde la session, redirige", async () => {
    server.use(http.post(`${API}/api/v1/auth/login`, () => HttpResponse.json({ success: true, message: "", data: { access_token: "tok", token_type: "bearer", user: { id: "u", first_name: "Lucas", email: "l@t.fr", role: "USER", subscription_plan: "STARTER" } } })));
    const { AuthForm } = await import("@/components/AuthForm");
    const { saveSession } = await import("@/lib/client-session");
    render(<AuthForm mode="login" />);
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "l@t.fr" } });
    fireEvent.change(screen.getByLabelText("Mot de passe"), { target: { value: "motdepasse123" } });
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    await waitFor(() => expect(saveSession).toHaveBeenCalledWith("tok"));
    expect(push).toHaveBeenCalledWith("/matchs");
  });
  it("inscription refusée avant 18 ans : le message de l'API s'affiche", async () => {
    server.use(http.post(`${API}/api/v1/auth/signup`, () => HttpResponse.json({ detail: [{ loc: ["body", "birth_date"], msg: "Value error, Vous devez avoir 18 ans ou plus" }] }, { status: 422 })));
    const { AuthForm } = await import("@/components/AuthForm");
    render(<AuthForm mode="signup" />);
    fireEvent.change(screen.getByLabelText("Prénom"), { target: { value: "Jeune" } });
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "j@t.fr" } });
    fireEvent.change(screen.getByLabelText("Mot de passe"), { target: { value: "motdepasse123" } });
    fireEvent.change(screen.getByLabelText("Date de naissance"), { target: { value: "2015-01-01" } });
    fireEvent.click(screen.getByLabelText(/J'ai 18 ans ou plus/));
    fireEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));
    expect(await screen.findByText("Vous devez avoir 18 ans ou plus")).toBeInTheDocument();
  });
  it("inscription : le bouton reste désactivé tant que la case 18 ans n'est pas cochée", async () => {
    const { AuthForm } = await import("@/components/AuthForm");
    render(<AuthForm mode="signup" />);
    expect(screen.getByRole("button", { name: "Créer mon compte" })).toBeDisabled();
  });
});
