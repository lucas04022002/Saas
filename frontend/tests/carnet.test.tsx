import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
// Le composant appelle désormais les Route Handlers same-origin (app/api/bankroll, app/api/matches) plutôt
// que l'API backend directement, pour ne jamais laisser transiter le jeton dans le HTML SSR (voir
// tests/api-routes.test.ts pour les Route Handlers eux-mêmes). En jsdom sous Vitest, window.location.origin
// vaut http://localhost:3000 : un fetch("/api/...") s'y résout, donc les handlers MSW doivent cibler cette
// origine absolue plutôt qu'un chemin relatif.
const APP = "http://localhost:3000";
const bet = { id: "b1", match_id: "m1", home_team: "Arsenal", away_team: "Chelsea", competition: "E0", kickoff_at: "2026-09-07T15:30:00Z", outcome: "home", bookmaker: "winamax_fr", odds: 2.05, stake: 40, status: "WON", payout: 82, created_at: "2026-09-06T10:00:00Z", settled_at: "2026-09-07T18:00:00Z", match_status: "SCHEDULED" };
const summary = { stakes: 90, settled_stakes: 40, payouts: 82, profit: 42, roi: 1.05, pending: 1, settled: 1, by_bookmaker: {}, by_competition: {} };
describe("carnet", () => {
  it("KPI, liste, statut, suppression d'un pari en attente", async () => {
    let deleted = "";
    server.use(
      http.get(`${APP}/api/bankroll`, () => HttpResponse.json({ success: true, message: "", data: { items: [bet, { ...bet, id: "b2", status: "PENDING", payout: null, stake: 50 }], summary } })),
      http.delete(`${APP}/api/bankroll/b2`, () => { deleted = "b2"; return HttpResponse.json({ success: true, message: "", data: { id: "b2" } }); }),
      http.get(`${APP}/api/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [], pagination: { page: 1, limit: 200, total: 0 } } })),
    );
    const { Bankroll } = await import("@/components/Bankroll");
    render(<Bankroll />);
    expect(await screen.findByText("Ton vrai bilan.")).toBeInTheDocument();
    expect(screen.getByText("90")).toBeInTheDocument();
    expect(screen.getByText("+42")).toBeInTheDocument();
    expect(screen.getByText("Gagné")).toBeInTheDocument();
    expect(screen.getByText("En attente")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Supprimer" }));
    await waitFor(() => expect(deleted).toBe("b2"));
  });
  it("saisie : envoie le pari et rafraîchit", async () => {
    let posted: unknown = null;
    server.use(
      http.get(`${APP}/api/bankroll`, () => HttpResponse.json({ success: true, message: "", data: { items: [], summary: { ...summary, stakes: 0, settled_stakes: 0, payouts: 0, profit: 0, roi: null, pending: 0, settled: 0 } } })),
      http.get(`${APP}/api/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [{ id: "m1", competition: "F1", league: "Ligue 1", home_team: "Lyon", away_team: "Marseille", kickoff_at: "2026-09-13T15:15:00Z", status: "SCHEDULED", favourite: null, reference: null, best_gap: null, movement: null, odds_taken_at: null, locked: false }], pagination: { page: 1, limit: 200, total: 1 } } })),
      http.post(`${APP}/api/bankroll`, async ({ request }) => { posted = await request.json(); return HttpResponse.json({ success: true, message: "", data: bet }, { status: 201 }); }),
    );
    const { Bankroll } = await import("@/components/Bankroll");
    render(<Bankroll preselected="m1" />);
    expect(await screen.findByText("Aucun pari noté. Le premier est en bas de page.")).toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText("Cote"), { target: { value: "1.78" } });
    fireEvent.change(screen.getByLabelText("Mise"), { target: { value: "50" } });
    fireEvent.click(screen.getByRole("button", { name: "Noter ce pari" }));
    await waitFor(() => expect(posted).toMatchObject({ match_id: "m1", outcome: "home", bookmaker: "betclic_fr", odds: 1.78, stake: 50 }));
  });
  it("annulation d'un pari en attente sur match reporté", async () => {
    let voided = "";
    server.use(
      http.get(`${APP}/api/bankroll`, () => HttpResponse.json({ success: true, message: "", data: { items: [{ ...bet, id: "b2", status: "PENDING", payout: null, stake: 50, match_status: "POSTPONED" }], summary } })),
      http.post(`${APP}/api/bankroll/b2/void`, () => { voided = "b2"; return HttpResponse.json({ success: true, message: "", data: { ...bet, id: "b2", status: "VOID" } }); }),
      http.get(`${APP}/api/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [], pagination: { page: 1, limit: 200, total: 0 } } })),
    );
    const { Bankroll } = await import("@/components/Bankroll");
    render(<Bankroll />);
    expect(await screen.findByText("Ton vrai bilan.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Supprimer" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Annuler" }));
    await waitFor(() => expect(voided).toBe("b2"));
  });
  it("liste : échec de chargement affiche une alerte et permet de réessayer", async () => {
    server.use(
      http.get(`${APP}/api/bankroll`, () => HttpResponse.json({ success: false, message: "boom" }, { status: 500 }), { once: true }),
      http.get(`${APP}/api/bankroll`, () => HttpResponse.json({ success: true, message: "", data: { items: [], summary: { ...summary, stakes: 0, settled_stakes: 0, payouts: 0, profit: 0, roi: null, pending: 0, settled: 0 } } })),
      http.get(`${APP}/api/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [], pagination: { page: 1, limit: 200, total: 0 } } })),
    );
    const { Bankroll } = await import("@/components/Bankroll");
    render(<Bankroll />);
    expect(await screen.findByText("Impossible de charger ton carnet. Réessaie dans un instant.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Aucun pari noté. Le premier est en bas de page.")).toBeInTheDocument();
  });
  it("suppression : échec affiche le message d'erreur", async () => {
    server.use(
      http.get(`${APP}/api/bankroll`, () => HttpResponse.json({ success: true, message: "", data: { items: [{ ...bet, id: "b2", status: "PENDING", payout: null, stake: 50 }], summary } })),
      http.delete(`${APP}/api/bankroll/b2`, () => HttpResponse.json({ success: false, message: "Only pending bets can be deleted" }, { status: 409 })),
      http.get(`${APP}/api/matches`, () => HttpResponse.json({ success: true, message: "", data: { items: [], pagination: { page: 1, limit: 200, total: 0 } } })),
    );
    const { Bankroll } = await import("@/components/Bankroll");
    render(<Bankroll />);
    fireEvent.click(await screen.findByRole("button", { name: "Supprimer" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Only pending bets can be deleted");
  });
});
