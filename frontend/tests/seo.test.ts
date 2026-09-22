import { describe, expect, it } from "vitest";
import robots from "@/app/robots";
import sitemap from "@/app/sitemap";

// robots.txt et sitemap.xml répondaient 404 (audit du 22/09/2026, F3). Aucun effet de sécurité ;
// un effet le jour où le site doit être trouvé.

describe("robots.txt", () => {
  it("autorise les pages publiques, exclut le compte, le carnet et les relais d'API", () => {
    const r = robots();
    const regles = Array.isArray(r.rules) ? r.rules : [r.rules];
    const principale = regles[0];
    expect(principale.allow).toBe("/");
    expect(principale.disallow).toEqual(expect.arrayContaining(["/compte", "/carnet", "/api/"]));
    expect(r.sitemap).toBe("https://rushplay.fr/sitemap.xml");
  });
});

describe("sitemap.xml", () => {
  it("liste les pages publiques, aucune page privée", () => {
    const urls = sitemap().map((e) => e.url);
    for (const p of ["/", "/matchs", "/bookmakers", "/track-record", "/tarifs", "/mentions-legales", "/cgu"]) {
      expect(urls).toContain(`https://rushplay.fr${p}`);
    }
    expect(urls.some((u) => u.includes("/compte") || u.includes("/carnet") || u.includes("/api/"))).toBe(false);
  });
});
