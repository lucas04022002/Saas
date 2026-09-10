import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";

// Les Route Handlers lisent/écrivent le cookie httpOnly via next/headers : on simule cookies() avec un
// jeton mutable et des journaux de set/delete, ajustés par chaque test avant d'appeler le handler (pas de
// rechargement de module nécessaire, cookies() est appelée à chaque requête, pas à l'import). Un appel
// direct au handler (hors du cycle de requête réel de Next.js) ne matérialise pas d'en-tête Set-Cookie sur
// la réponse : on vérifie donc que cookies().set()/.delete() ont bien été invoqués, ce qui est le
// comportement observable équivalent pour cette couche.
const cookieStore = vi.hoisted(() => ({ token: undefined as string | undefined, sets: [] as { name: string; value: string }[], deletes: [] as string[] }));
vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => (name === "rp_token" && cookieStore.token !== undefined ? { value: cookieStore.token } : undefined),
    set: (name: string, value: string) => { cookieStore.sets.push({ name, value }); },
    delete: (name: string) => { cookieStore.deletes.push(name); },
  }),
}));

describe("app/api/bankroll — proxy authentifié", () => {
  it("sans cookie : 401 sans appeler le backend", async () => {
    cookieStore.token = undefined;
    const { GET } = await import("@/app/api/bankroll/route");
    const res = await GET();
    expect(res.status).toBe(401);
    expect(await res.json()).toEqual({ success: false, message: "Non connecté" });
  });

  it("avec cookie : proxie vers le backend et renvoie l'enveloppe", async () => {
    cookieStore.token = "tok";
    server.use(
      http.get(`${API}/api/v1/bankroll`, ({ request }) => {
        expect(request.headers.get("authorization")).toBe("Bearer tok");
        return HttpResponse.json({ success: true, message: "", data: { items: [], summary: { stakes: 0 } } });
      }),
    );
    const { GET } = await import("@/app/api/bankroll/route");
    const res = await GET();
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ success: true, message: "", data: { items: [], summary: { stakes: 0 } } });
  });

  it("le jeton n'apparaît dans aucune réponse de la route", async () => {
    cookieStore.token = "un-jeton-secret";
    server.use(http.get(`${API}/api/v1/bankroll`, () => HttpResponse.json({ success: true, message: "", data: { items: [], summary: { stakes: 0 } } })));
    const { GET } = await import("@/app/api/bankroll/route");
    const res = await GET();
    const text = JSON.stringify(await res.json());
    expect(text).not.toContain("un-jeton-secret");
  });

  it("erreur backend (ApiError) : le statut et le message sont propagés", async () => {
    cookieStore.token = "tok";
    server.use(http.get(`${API}/api/v1/bankroll`, () => HttpResponse.json({ success: false, message: "boom" }, { status: 500 })));
    const { GET } = await import("@/app/api/bankroll/route");
    const res = await GET();
    expect(res.status).toBe(500);
    expect(await res.json()).toEqual({ success: false, message: "boom" });
  });

  it("POST : une requête d'origine étrangère est aussi refusée (403)", async () => {
    cookieStore.token = "tok";
    const { POST } = await import("@/app/api/bankroll/route");
    const req = new Request("http://localhost:3000/api/bankroll", { method: "POST", headers: { origin: "https://evil.example" }, body: "{}" });
    const res = await POST(req);
    expect(res.status).toBe(403);
  });

  it("POST same-origin avec cookie : 201 et le pari créé", async () => {
    cookieStore.token = "tok";
    const bet = { id: "b1", match_id: "m1", outcome: "home", bookmaker: "winamax_fr", odds: 1.78, stake: 10, status: "PENDING" };
    server.use(http.post(`${API}/api/v1/bankroll`, () => HttpResponse.json({ success: true, message: "", data: bet }, { status: 201 })));
    const { POST } = await import("@/app/api/bankroll/route");
    const req = new Request("http://localhost:3000/api/bankroll", {
      method: "POST",
      headers: { "sec-fetch-site": "same-origin", "content-type": "application/json" },
      body: JSON.stringify({ match_id: "m1", outcome: "home", bookmaker: "winamax_fr", odds: 1.78, stake: 10 }),
    });
    const res = await POST(req);
    expect(res.status).toBe(201);
    expect(await res.json()).toEqual({ success: true, message: "", data: bet });
  });

  it("POST same-origin avec un corps qui n'est pas du JSON : 400, sans appeler le backend", async () => {
    cookieStore.token = "tok";
    const { POST } = await import("@/app/api/bankroll/route");
    const req = new Request("http://localhost:3000/api/bankroll", {
      method: "POST",
      headers: { "sec-fetch-site": "same-origin", "content-type": "application/json" },
      body: "pas du json",
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ success: false, message: "Corps de requête invalide" });
  });

  it("DELETE /[id] : le statut du backend est propagé tel quel", async () => {
    cookieStore.token = "tok";
    server.use(http.delete(`${API}/api/v1/bankroll/b1`, () => HttpResponse.json({ success: false, message: "Bet not found" }, { status: 404 })));
    const { DELETE } = await import("@/app/api/bankroll/[id]/route");
    const req = new Request("http://localhost:3000/api/bankroll/b1", { method: "DELETE", headers: { "sec-fetch-site": "same-origin" } });
    const res = await DELETE(req, { params: Promise.resolve({ id: "b1" }) });
    expect(res.status).toBe(404);
    expect(await res.json()).toEqual({ success: false, message: "Bet not found" });
  });

  it("POST /[id]/void : le statut du backend est propagé tel quel", async () => {
    cookieStore.token = "tok";
    server.use(http.post(`${API}/api/v1/bankroll/b1/void`, () => HttpResponse.json({ success: false, message: "Only pending bets on postponed matches can be voided" }, { status: 409 })));
    const { POST: VOID } = await import("@/app/api/bankroll/[id]/void/route");
    const req = new Request("http://localhost:3000/api/bankroll/b1/void", { method: "POST", headers: { "sec-fetch-site": "same-origin" } });
    const res = await VOID(req, { params: Promise.resolve({ id: "b1" }) });
    expect(res.status).toBe(409);
    expect(await res.json()).toEqual({ success: false, message: "Only pending bets on postponed matches can be voided" });
  });
});

describe("app/api/session — garde d'origine (CSRF)", () => {
  it("POST sans sec-fetch-site, origine étrangère : 403", async () => {
    const { POST } = await import("@/app/api/session/route");
    const req = new Request("http://localhost:3000/api/session", { method: "POST", headers: { origin: "https://evil.example", "content-type": "application/json" }, body: JSON.stringify({ token: "x" }) });
    const res = await POST(req);
    expect(res.status).toBe(403);
    expect(await res.json()).toEqual({ success: false, message: "Origine refusée" });
  });

  it("POST avec sec-fetch-site: same-origin : 200 et le cookie est posé", async () => {
    cookieStore.sets = [];
    const { POST } = await import("@/app/api/session/route");
    const req = new Request("http://localhost:3000/api/session", { method: "POST", headers: { "sec-fetch-site": "same-origin", "content-type": "application/json" }, body: JSON.stringify({ token: "x" }) });
    const res = await POST(req);
    expect(res.status).toBe(200);
    expect(cookieStore.sets).toContainEqual(expect.objectContaining({ name: "rp_token", value: "x" }));
  });

  it("DELETE sans sec-fetch-site ni origin same-site : 403", async () => {
    const { DELETE } = await import("@/app/api/session/route");
    const req = new Request("http://localhost:3000/api/session", { method: "DELETE", headers: { origin: "https://evil.example" } });
    const res = await DELETE(req);
    expect(res.status).toBe(403);
  });

  it("DELETE avec sec-fetch-site: same-origin : 200 et le cookie est retiré", async () => {
    cookieStore.deletes = [];
    const { DELETE } = await import("@/app/api/session/route");
    const req = new Request("http://localhost:3000/api/session", { method: "DELETE", headers: { "sec-fetch-site": "same-origin" } });
    const res = await DELETE(req);
    expect(res.status).toBe(200);
    expect(cookieStore.deletes).toContain("rp_token");
  });
});
