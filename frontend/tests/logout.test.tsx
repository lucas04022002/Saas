import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/envelope";

const push = vi.fn();
const refresh = vi.fn();
const clearSession = vi.fn(async () => {});
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, refresh }) }));
vi.mock("@/lib/client-session", () => ({ clearSession: () => clearSession() }));

beforeEach(() => {
  push.mockClear();
  refresh.mockClear();
  clearSession.mockClear().mockImplementation(async () => {});
});

describe("Se déconnecter", () => {
  it("depuis la barre de navigation : ferme la session et ramène à l'accueil", async () => {
    const { LogoutButton } = await import("@/components/LogoutButton");
    render(<LogoutButton variant="nav" />);

    fireEvent.click(screen.getByRole("button", { name: "Se déconnecter" }));

    await waitFor(() => expect(clearSession).toHaveBeenCalled());
    expect(push).toHaveBeenCalledWith("/");
    // Sans `refresh`, la barre continuerait d'afficher le prénom : le rendu
    // serveur est en cache et ne sait pas que le cookie vient de tomber.
    expect(refresh).toHaveBeenCalled();
  });

  it("depuis la page Compte : même geste, même effet", async () => {
    const { LogoutButton } = await import("@/components/LogoutButton");
    render(<LogoutButton />);

    fireEvent.click(screen.getByRole("button", { name: "Se déconnecter" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
  });

  it("si le cookie n'a pas pu être retiré, on ne redirige pas", async () => {
    // Le vrai risque : renvoyer vers l'accueil avec la session encore ouverte.
    // L'utilisateur s'éloigne de l'écran en croyant s'être déconnecté.
    clearSession.mockImplementation(async () => {
      throw new ApiError(500, "Déconnexion impossible");
    });
    const { LogoutButton } = await import("@/components/LogoutButton");
    render(<LogoutButton variant="nav" />);

    fireEvent.click(screen.getByRole("button", { name: "Se déconnecter" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Déconnexion impossible");
    expect(push).not.toHaveBeenCalled();
  });
});
