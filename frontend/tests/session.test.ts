import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";

vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => ({ value: "tok" }) }) }));

describe("getUser — API injoignable", () => {
  it("réseau en erreur : résout null au lieu de faire planter la page", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.get(`${API}/api/v1/auth/me`, () => HttpResponse.error()));
    const { getUser } = await import("@/lib/session");
    await expect(getUser()).resolves.toBeNull();
    expect(spy).toHaveBeenCalled();
    spy.mockRestore();
  });

  it("500 côté API : résout null aussi (pas seulement les erreurs applicatives)", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.get(`${API}/api/v1/auth/me`, () => HttpResponse.json({ success: false, message: "boom" }, { status: 500 })));
    const { getUser } = await import("@/lib/session");
    await expect(getUser()).resolves.toBeNull();
    spy.mockRestore();
  });
});
