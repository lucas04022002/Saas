import { describe, expect, it } from "vitest";
import { buildCsp } from "@/lib/csp";

// Pas de Content-Security-Policy sur le site (audit du 22/09/2026, M2). Le jeton est en cookie httpOnly,
// mais un script injecté pourrait appeler les Route Handlers au nom de l'utilisateur.

describe("Content-Security-Policy", () => {
  const prod = buildCsp("abc123", { apiOrigin: "https://api.rushplay.fr", dev: false });

  it("les scripts ne passent que par le nonce de la requête", () => {
    expect(prod).toMatch(/script-src [^;]*'nonce-abc123'/);
    expect(prod).toMatch(/script-src [^;]*'strict-dynamic'/);
    expect(prod).not.toContain("unsafe-eval");
  });

  it("le navigateur ne peut joindre que le site et l'API", () => {
    expect(prod).toMatch(/connect-src 'self' https:\/\/api\.rushplay\.fr(;|$)/);
  });

  it("aucun cadre, aucune base détournée, aucun plugin", () => {
    expect(prod).toContain("frame-ancestors 'none'");
    expect(prod).toContain("base-uri 'self'");
    expect(prod).toContain("object-src 'none'");
    expect(prod).toContain("form-action 'self'");
  });

  it("images et polices : locales seulement", () => {
    expect(prod).toMatch(/img-src 'self'/);
    expect(prod).toMatch(/font-src 'self'/);
  });

  it("en développement, l'outillage de Next (eval, websocket) est tolé­ré", () => {
    const dev = buildCsp("n", { apiOrigin: "http://127.0.0.1:8000", dev: true });
    expect(dev).toContain("'unsafe-eval'");
    expect(dev).toMatch(/connect-src [^;]*ws:/);
  });
});
