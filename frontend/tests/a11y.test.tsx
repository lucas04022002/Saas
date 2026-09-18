import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => undefined }) }));
const empty = () => HttpResponse.json({ success: true, message: "", data: { items: [], pagination: { page: 1, limit: 50, total: 0 }, quota: { plan: "ANONYMOUS", limit: 0, used: 0, remaining: 0, resets_at: null }, note: "n" } });
describe("accessibilité de base", () => {
  it("un seul h1 par page, alt sur les images, en-têtes de tableau", async () => {
    server.use(http.get(`${API}/api/v1/matches`, empty), http.get(`${API}/api/v1/track-record`, empty));
    for (const mod of ["@/app/page", "@/app/matchs/page", "@/app/track-record/page", "@/app/tarifs/page"]) {
      const Page = (await import(mod)).default;
      const { container, unmount } = render(await Page({ searchParams: Promise.resolve({}) }));
      expect(container.querySelectorAll("h1").length, mod).toBe(1);
      container.querySelectorAll("img").forEach((img) => expect(img.hasAttribute("alt"), mod).toBe(true));
      container.querySelectorAll("table").forEach((t) => expect(t.querySelectorAll("th").length, mod).toBeGreaterThan(0));
      unmount();
    }
  });
  it("le pied de page porte le numéro d'aide", async () => {
    const { Footer } = await import("@/components/Footer");
    const { container } = render(await Footer());
    expect(container.textContent).toContain("09 74 75 13 13");
  });
});
