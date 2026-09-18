import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }) }));

function repond(status: number, body: unknown) {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })));
}

describe("BillingButton : ce que voit l'utilisateur quand ça échoue", () => {
  it("un refus de Stripe affiche son motif, pas « réessayez »", async () => {
    // Le vrai risque : « réessayez dans un instant » invite à recommencer un
    // geste qui ne peut pas aboutir, et cache la cause aux deux bouts.
    repond(502, { success: false, message: "Stripe a refusé la création du paiement (url_invalid).", data: null });
    const { BillingButton } = await import("@/components/BillingButton");
    render(<BillingButton action="checkout" label="S'abonner" />);

    fireEvent.click(screen.getByRole("button", { name: "S'abonner" }));

    expect(await screen.findByText(/url_invalid/)).toBeInTheDocument();
  });

  it("sans message du serveur, le texte générique reste", async () => {
    repond(500, { success: false, message: "", data: null });
    const { BillingButton } = await import("@/components/BillingButton");
    render(<BillingButton action="checkout" label="S'abonner" />);

    fireEvent.click(screen.getByRole("button", { name: "S'abonner" }));

    expect(await screen.findByText(/Réessayez dans un instant/)).toBeInTheDocument();
  });

  it("paiement non configuré : message dédié, pas le jargon du serveur", async () => {
    repond(503, { success: false, message: "Le paiement en ligne n'est pas encore ouvert. Réessayez plus tard.", data: null });
    const { BillingButton } = await import("@/components/BillingButton");
    render(<BillingButton action="checkout" label="S'abonner" />);

    fireEvent.click(screen.getByRole("button", { name: "S'abonner" }));

    expect(await screen.findByText("Le paiement en ligne n'est pas encore ouvert.")).toBeInTheDocument();
  });
});
