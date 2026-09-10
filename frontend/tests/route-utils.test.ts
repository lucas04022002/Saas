import { describe, expect, it, vi } from "vitest";

// route-utils importe lib/session, qui lit le cookie via next/headers : on le neutralise, ces tests
// ne portent que sur la garde d'origine.
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => undefined }) }));

const { originGuard } = await import("@/lib/route-utils");

describe("originGuard", () => {
  it("sec-fetch-site: same-origin laisse passer", () => {
    const req = new Request("https://rushplay.fr/api/session", { method: "POST", headers: { "sec-fetch-site": "same-origin" } });
    expect(originGuard(req)).toBeNull();
  });

  it("derrière un proxy qui termine le TLS : Origin en https, requête vue en http, même hôte → autorisée", () => {
    // Le proxy transmet la requête en clair : Next.js voit http://rushplay.fr/… alors que le
    // navigateur a annoncé Origin: https://rushplay.fr. Comparer les origines complètes produirait
    // un 403 en production sur une requête parfaitement légitime.
    const req = new Request("http://rushplay.fr/api/bankroll", { method: "POST", headers: { origin: "https://rushplay.fr" } });
    expect(originGuard(req)).toBeNull();
  });

  it("un hôte étranger reste refusé (403), même en https des deux côtés", () => {
    const req = new Request("https://rushplay.fr/api/bankroll", { method: "POST", headers: { origin: "https://evil.example" } });
    const res = originGuard(req);
    expect(res).not.toBeNull();
    expect(res!.status).toBe(403);
  });

  it("un sous-domaine étranger reste refusé", () => {
    const req = new Request("https://rushplay.fr/api/bankroll", { method: "POST", headers: { origin: "https://evil.rushplay.fr.attacker.example" } });
    expect(originGuard(req)!.status).toBe(403);
  });

  it("un port différent reste refusé (l'hôte inclut le port)", () => {
    const req = new Request("http://rushplay.fr:3000/api/bankroll", { method: "POST", headers: { origin: "http://rushplay.fr:4000" } });
    expect(originGuard(req)!.status).toBe(403);
  });

  it("Origin illisible (« null ») : refusé", () => {
    const req = new Request("https://rushplay.fr/api/bankroll", { method: "POST", headers: { origin: "null" } });
    expect(originGuard(req)!.status).toBe(403);
  });

  it("ni sec-fetch-site ni Origin : refusé", () => {
    const req = new Request("https://rushplay.fr/api/bankroll", { method: "POST" });
    expect(originGuard(req)!.status).toBe(403);
  });
});
