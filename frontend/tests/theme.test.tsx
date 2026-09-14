import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { THEME_ATTR, THEME_KEY, THEME_SCRIPT, readTheme } from "@/lib/theme";
import { ThemeToggle } from "@/components/ThemeToggle";

// jsdom n'applique pas la feuille de style : ce qui est vérifiable ici, c'est l'attribut posé sur
// <html> (le pivot du thème) et la source CSS qui le branche sur les bonnes règles.
const css = readFileSync(path.resolve(__dirname, "../app/globals.css"), "utf8");

function runInlineScript() {
  new Function(THEME_SCRIPT)();
}

// Node 25 expose un `localStorage` global vide qui masque celui de jsdom : on pose un vrai
// stockage sur `window` pour chaque test, c'est lui que lit `lib/theme` (et le script inline).
let store: Map<string, string>;
function installStorage(impl?: Partial<Storage>) {
  store = new Map();
  const fake: Storage = {
    get length() { return store.size; },
    clear: () => store.clear(),
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    key: (i: number) => [...store.keys()][i] ?? null,
    removeItem: (k: string) => { store.delete(k); },
    setItem: (k: string, v: string) => { store.set(k, String(v)); },
    ...impl,
  };
  Object.defineProperty(window, "localStorage", { value: fake, configurable: true, writable: true });
}

beforeEach(() => {
  installStorage();
  document.documentElement.removeAttribute(THEME_ATTR);
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe("script inline (avant la première peinture)", () => {
  it("sans choix stocké, il ne pose rien : c'est la media query système qui décide", () => {
    runInlineScript();
    expect(document.documentElement.hasAttribute(THEME_ATTR)).toBe(false);
  });
  it("choix « sombre » stocké : data-theme=dark", () => {
    window.localStorage.setItem(THEME_KEY, "dark");
    runInlineScript();
    expect(document.documentElement.getAttribute(THEME_ATTR)).toBe("dark");
  });
  it("choix « clair » stocké : data-theme=light, qui doit gagner sur un système sombre", () => {
    window.localStorage.setItem(THEME_KEY, "light");
    runInlineScript();
    expect(document.documentElement.getAttribute(THEME_ATTR)).toBe("light");
  });
  it("valeur stockée aberrante : on retombe sur le système, jamais sur un attribut bancal", () => {
    window.localStorage.setItem(THEME_KEY, "néon");
    document.documentElement.setAttribute(THEME_ATTR, "dark");
    runInlineScript();
    expect(document.documentElement.hasAttribute(THEME_ATTR)).toBe(false);
  });
  it("stockage interdit (navigation privée, cookies bloqués) : ni exception ni attribut", () => {
    installStorage({ getItem: () => { throw new Error("stockage bloqué"); } });
    expect(() => runInlineScript()).not.toThrow();
    expect(document.documentElement.hasAttribute(THEME_ATTR)).toBe(false);
    expect(readTheme()).toBe("system");
  });
});

describe("la CSS branche les trois positions", () => {
  it("la palette système est gardée par :not([data-theme=\"light\"]) — un choix clair reprend la main", () => {
    expect(css).toMatch(/@media \(prefers-color-scheme: dark\) \{ :root:not\(\[data-theme="light"\]\) \{ color-scheme: dark; \} \}/);
  });
  it("le choix explicite « sombre » vaut quel que soit le système", () => {
    expect(css).toMatch(/:root\[data-theme="dark"\] \{\s*color-scheme: dark;\s*\}/);
  });
  it("le thème clair reste la valeur par défaut du :root", () => {
    expect(css).toMatch(/:root \{ color-scheme: light; \}/);
  });
});

describe("sélecteur Système / Clair / Sombre", () => {
  it("affiche les trois positions et part sur « Système »", () => {
    render(<ThemeToggle />);
    for (const label of ["Système", "Clair", "Sombre"]) expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Système" })).toHaveAttribute("aria-pressed", "true");
    expect(document.documentElement.hasAttribute(THEME_ATTR)).toBe(false);
  });

  it("« Sombre » puis « Clair » puis « Système » : attribut et stockage suivent", () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: "Sombre" }));
    expect(document.documentElement.getAttribute(THEME_ATTR)).toBe("dark");
    expect(window.localStorage.getItem(THEME_KEY)).toBe("dark");
    expect(screen.getByRole("button", { name: "Sombre" })).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(screen.getByRole("button", { name: "Clair" }));
    expect(document.documentElement.getAttribute(THEME_ATTR)).toBe("light");
    expect(window.localStorage.getItem(THEME_KEY)).toBe("light");

    fireEvent.click(screen.getByRole("button", { name: "Système" }));
    expect(document.documentElement.hasAttribute(THEME_ATTR)).toBe(false);
    expect(window.localStorage.getItem(THEME_KEY)).toBeNull();
  });

  it("un choix déjà stocké est repris au montage, avant la peinture", () => {
    window.localStorage.setItem(THEME_KEY, "dark");
    render(<ThemeToggle />);
    expect(screen.getByRole("button", { name: "Sombre" })).toHaveAttribute("aria-pressed", "true");
    expect(document.documentElement.getAttribute(THEME_ATTR)).toBe("dark");
  });

  it("le groupe est annoncé comme tel", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("group", { name: "Thème" })).toBeInTheDocument();
  });
});
