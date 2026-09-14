import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";

// Le contraste des jetons de couleur est vérifié sur le fichier source : si un jeton change,
// le test échoue avant que le gris illisible n'atteigne la page. Depuis le mode sombre, chaque
// jeton porte ses deux valeurs — `light-dark(clair, sombre)` — et les DEUX palettes sont testées.
const css = readFileSync(path.resolve(__dirname, "../app/globals.css"), "utf8");

type Palette = Record<string, string>;

function block(from: string, to: string): string {
  const a = css.indexOf(from);
  const b = css.indexOf(to);
  if (a === -1 || b === -1) throw new Error(`bloc ${from}…${to} introuvable dans app/globals.css`);
  return css.slice(a + from.length, b);
}

// Normalise #abc → aabbcc ; renvoie null pour ce qui n'est pas un hexadécimal (rgba des filets).
function hex(value: string): string | null {
  const m = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.exec(value.trim());
  if (!m) return null;
  const h = m[1];
  return h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
}

// Lit les déclarations `--rp-nom: light-dark(clair, sombre)` (ou une valeur unique) d'un bloc.
function palettes(source: string): { light: Palette; dark: Palette } {
  const light: Palette = {};
  const dark: Palette = {};
  for (const m of source.matchAll(/--rp-([a-z-]+):\s*([^;]+);/g)) {
    const [name, raw] = [m[1], m[2].trim()];
    const ld = /^light-dark\(([^,]+),(.+)\)$/.exec(raw);
    const [l, d] = ld ? [ld[1], ld[2]] : [raw, raw];
    const [lh, dh] = [hex(l), hex(d)];
    if (lh) light[name] = lh;
    if (dh) dark[name] = dh;
  }
  return { light, dark };
}

const root = palettes(block("/* palette:début */", "/* palette:fin */"));
// Dans une bande `bg-black`, « paper » redevient la couleur claire : c'est ce jeton-là que
// porte le texte des sections noires, pas celui du :root.
const island = palettes(block("/* îlot:début */", "/* îlot:fin */"));

function luminance(h: string): number {
  const channels = [0, 2, 4].map((i) => {
    const c = parseInt(h.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function ratio(a: string, b: string): number {
  const [la, lb] = [luminance(a), luminance(b)];
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

function token(p: Palette, name: string): string {
  const v = p[name];
  if (!v) throw new Error(`jeton --rp-${name} introuvable dans app/globals.css`);
  return v;
}

// [premier plan, fond] — `paper@black` = le « paper » réinversé de l'îlot des bandes noires.
const NORMAL: [string, string][] = [
  ["link", "paper"],
  ["link", "grey"],
  ["faint-text", "paper"],
  ["faint-text", "grey"],
  ["muted", "paper"],
  ["muted", "grey"],
  ["ink", "paper"],
  ["paper", "ink"],
  ["ink", "segment"],
  ["ink", "segment-on"],
  ["faint-dark", "black"],
  ["nav-muted", "black"],
  ["photo-text", "black"],
  ["paper@black", "black"],
];

// Jetons réservés aux très grands nombres (num-row, num-page) : seuil WCAG « grand texte ».
const LARGE: [string, string][] = [
  ["faint", "paper"],
  ["faint", "grey"],
];

function resolve(theme: "light" | "dark", name: string): string {
  if (name.endsWith("@black")) return token(island[theme], name.slice(0, -"@black".length));
  return token(root[theme], name);
}

for (const theme of ["light", "dark"] as const) {
  describe(`contraste des jetons — palette ${theme === "light" ? "claire" : "sombre"}`, () => {
    for (const [fg, bg] of NORMAL) {
      it(`${fg} sur ${bg} atteint 4,5:1`, () => {
        expect(ratio(resolve(theme, fg), resolve(theme, bg))).toBeGreaterThanOrEqual(4.5);
      });
    }
    for (const [fg, bg] of LARGE) {
      it(`${fg} sur ${bg} atteint 3:1 (grand texte)`, () => {
        expect(ratio(resolve(theme, fg), resolve(theme, bg))).toBeGreaterThanOrEqual(3);
      });
    }
  });
}

describe("les deux palettes existent", () => {
  it("chaque jeton hexadécimal du :root a une valeur claire et une valeur sombre", () => {
    expect(Object.keys(root.light).sort()).toEqual(Object.keys(root.dark).sort());
    expect(Object.keys(root.light).length).toBeGreaterThan(10);
  });
  it("la palette sombre diffère vraiment de la claire", () => {
    const changed = Object.keys(root.light).filter((k) => root.light[k] !== root.dark[k]);
    expect(changed).toContain("paper");
    expect(changed).toContain("ink");
    expect(changed).toContain("black");
  });
});
