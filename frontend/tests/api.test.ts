import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { api, ApiError } from "@/lib/api";

const API = "http://localhost:8000";

describe("client API", () => {
  it("déballe data sur succès", async () => {
    server.use(http.get(`${API}/api/v1/legal`, () => HttpResponse.json({ success: true, message: "ok", data: { warning: "W", minimum_age: 18, positioning: "P" } })));
    const legal = await api.legal();
    expect(legal.minimum_age).toBe(18);
  });

  it("lève ApiError avec le message de l'API sur erreur HTTPException", async () => {
    server.use(http.get(`${API}/api/v1/matches/xyz`, () => HttpResponse.json({ success: false, message: "Match not found" }, { status: 404 })));
    await expect(api.match("xyz")).rejects.toMatchObject({ status: 404, message: "Match not found" });
  });

  it("lève ApiError avec le premier message de validation sur 422", async () => {
    server.use(http.post(`${API}/api/v1/auth/signup`, () => HttpResponse.json({ detail: [{ loc: ["body", "birth_date"], msg: "Value error, Vous devez avoir 18 ans ou plus" }] }, { status: 422 })));
    await expect(api.signup({ first_name: "A", email: "a@a.fr", password: "motdepasse123", birth_date: "2015-01-01" })).rejects.toBeInstanceOf(ApiError);
    await expect(api.signup({ first_name: "A", email: "a@a.fr", password: "motdepasse123", birth_date: "2015-01-01" })).rejects.toMatchObject({ message: "Vous devez avoir 18 ans ou plus" });
  });

  it("envoie le jeton en Authorization quand il est fourni", async () => {
    let auth = "";
    server.use(http.get(`${API}/api/v1/bankroll`, ({ request }) => { auth = request.headers.get("authorization") ?? ""; return HttpResponse.json({ success: true, message: "", data: { items: [], summary: {} } }); }));
    await api.bankroll.list("tok");
    expect(auth).toBe("Bearer tok");
  });
});
