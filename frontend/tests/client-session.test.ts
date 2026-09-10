import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { ApiError } from "@/lib/api";
import { clearSession, saveSession } from "@/lib/client-session";

// jsdom sert les tests depuis http://localhost:3000 : la route relative /api/session s'y résout.
const SESSION = "http://localhost:3000/api/session";

describe("client-session", () => {
  it("saveSession : une réponse 403 remonte le message du serveur", async () => {
    server.use(http.post(SESSION, () => HttpResponse.json({ success: false, message: "Origine refusée" }, { status: 403 })));
    await expect(saveSession("t")).rejects.toThrow("Origine refusée");
  });

  it("saveSession : le statut de l'ApiError est celui de la réponse", async () => {
    server.use(http.post(SESSION, () => HttpResponse.json({ success: false, message: "Origine refusée" }, { status: 403 })));
    await expect(saveSession("t")).rejects.toMatchObject({ name: "ApiError", status: 403 });
  });

  it("saveSession : sans message dans l'enveloppe, le texte de repli est utilisé", async () => {
    server.use(http.post(SESSION, () => HttpResponse.json({ ok: false }, { status: 400 })));
    await expect(saveSession("t")).rejects.toThrow("Session refusée");
  });

  it("saveSession : une réponse 200 ne lève rien", async () => {
    server.use(http.post(SESSION, () => HttpResponse.json({ ok: true })));
    await expect(saveSession("t")).resolves.toBeUndefined();
  });

  it("clearSession : une réponse 403 lève une ApiError", async () => {
    server.use(http.delete(SESSION, () => HttpResponse.json({ success: false, message: "Origine refusée" }, { status: 403 })));
    await expect(clearSession()).rejects.toBeInstanceOf(ApiError);
  });

  it("clearSession : une réponse 200 ne lève rien", async () => {
    server.use(http.delete(SESSION, () => HttpResponse.json({ ok: true })));
    await expect(clearSession()).resolves.toBeUndefined();
  });
});
