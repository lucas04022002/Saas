import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";

// Les Route Handlers lisent le cookie httpOnly via next/headers : on simule cookies() avec un jeton
// mutable, ajusté par chaque test avant d'appeler le handler (pas de rechargement de module nécessaire,
// cookies() est appelée à chaque requête, pas à l'import).
const cookieStore = vi.hoisted(() => ({ token: undefined as string | undefined }));
vi.mock("next/headers", () => ({
  cookies: async () => ({ get: (name: string) => (name === "rp_token" && cookieStore.token !== undefined ? { value: cookieStore.token } : undefined) }),
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
});
