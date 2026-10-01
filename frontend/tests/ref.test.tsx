import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";
import { API } from "./msw/handlers";
import { REF_DUREE_MS, REF_KEY, captureRef, sourceGardee, sourceValide } from "@/lib/ref";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }) }));
vi.mock("@/lib/client-session", () => ({ saveSession: vi.fn(async () => {}), clearSession: vi.fn(async () => {}) }));

// Node 25 masque le localStorage de jsdom (voir theme.test.tsx) : un vrai stockage par test.
let store: Map<string, string>;
beforeEach(() => {
  store = new Map();
  const fake = {
    get length() { return store.size; },
    clear: () => store.clear(),
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    key: (i: number) => [...store.keys()][i] ?? null,
    removeItem: (k: string) => { store.delete(k); },
    setItem: (k: string, v: string) => { store.set(k, String(v)); },
  } as Storage;
  Object.defineProperty(window, "localStorage", { value: fake, configurable: true, writable: true });
  window.history.replaceState(null, "", "/");
});

describe("lien de mesure ?ref=", () => {
  it("liste fermée, casse ignorée", () => {
    expect(sourceValide(" TikTok ")).toBe("tiktok");
    expect(sourceValide("pirate")).toBeNull();
    expect(sourceValide(null)).toBeNull();
  });

  it("à l'arrivée : une visite envoyée, la source gardée, ?ref retiré de l'adresse (le reste gardé)", () => {
    window.history.replaceState(null, "", "/matchs?ref=tiktok&ligue=F1#haut");
    const envoyer = vi.fn(async () => null);
    expect(captureRef(envoyer)).toBe("tiktok");
    expect(envoyer).toHaveBeenCalledExactlyOnceWith("tiktok");
    expect(window.location.pathname + window.location.search + window.location.hash).toBe("/matchs?ligue=F1#haut");
    expect(sourceGardee()).toBe("tiktok");
  });

  it("un rechargement après coup ne compte pas une deuxième visite", () => {
    window.history.replaceState(null, "", "/?ref=insta");
    const envoyer = vi.fn(async () => null);
    captureRef(envoyer);
    captureRef(envoyer); // l'adresse n'a plus ?ref
    expect(envoyer).toHaveBeenCalledTimes(1);
  });

  it("source inconnue : rien d'envoyé ni gardé, mais l'adresse est nettoyée", () => {
    window.history.replaceState(null, "", "/?ref=pirate");
    const envoyer = vi.fn(async () => null);
    expect(captureRef(envoyer)).toBeNull();
    expect(envoyer).not.toHaveBeenCalled();
    expect(store.has(REF_KEY)).toBe(false);
    expect(window.location.search).toBe("");
  });

  it("sans ?ref : rien ne se passe", () => {
    const envoyer = vi.fn(async () => null);
    expect(captureRef(envoyer)).toBeNull();
    expect(envoyer).not.toHaveBeenCalled();
  });

  it("la source expire après 30 jours", () => {
    store.set(REF_KEY, JSON.stringify({ s: "tiktok", t: 1_000 }));
    expect(sourceGardee(1_000 + REF_DUREE_MS - 1)).toBe("tiktok");
    expect(sourceGardee(1_000 + REF_DUREE_MS + 1)).toBeNull();
    expect(store.has(REF_KEY)).toBe(false);
  });

  it("un serveur injoignable ne casse rien", async () => {
    window.history.replaceState(null, "", "/?ref=tiktok");
    expect(captureRef(() => Promise.reject(new Error("réseau")))).toBe("tiktok");
    await Promise.resolve();
  });

  it("le vrai appel part vers /api/v1/visits", async () => {
    let recu: unknown = null;
    server.use(http.post(`${API}/api/v1/visits`, async ({ request }) => {
      recu = await request.json();
      return HttpResponse.json({ success: true, message: "ok", data: null });
    }));
    window.history.replaceState(null, "", "/?ref=insta");
    captureRef();
    await waitFor(() => expect(recu).toEqual({ source: "insta" }));
  });
});

describe("inscription : la source suit le compte", () => {
  async function inscrire() {
    let corps: Record<string, unknown> = {};
    server.use(http.post(`${API}/api/v1/auth/signup`, async ({ request }) => {
      corps = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({ success: true, message: "", data: { access_token: "tok", token_type: "bearer", user: { id: "u", first_name: "Lucas", email: "l@t.fr", role: "USER", subscription_plan: "STARTER" } } });
    }));
    const { AuthForm } = await import("@/components/AuthForm");
    render(<AuthForm mode="signup" />);
    fireEvent.change(screen.getByLabelText("Prénom"), { target: { value: "Lucas" } });
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "l@t.fr" } });
    fireEvent.change(screen.getByLabelText("Mot de passe"), { target: { value: "motdepasse123" } });
    fireEvent.change(screen.getByLabelText("Date de naissance"), { target: { value: "2000-01-01" } });
    fireEvent.click(screen.getByLabelText(/J'ai 18 ans ou plus/));
    fireEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));
    await waitFor(() => expect(corps.email).toBe("l@t.fr"));
    return corps;
  }

  it("arrivé par TikTok : source « tiktok » envoyée", async () => {
    store.set(REF_KEY, JSON.stringify({ s: "tiktok", t: Date.now() }));
    expect((await inscrire()).source).toBe("tiktok");
  });

  it("arrivé autrement : pas de champ source", async () => {
    expect("source" in (await inscrire())).toBe(false);
  });
});
