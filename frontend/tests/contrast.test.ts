import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";

// Le contraste des jetons de couleur est vérifié sur le fichier source : si un jeton change,
// le test échoue avant que le gris illisible n'atteigne la page.
const css = readFileSync(path.resolve(__dirname, "../app/globals.css"), "utf8");

function token(name: string): string {
  const m = new RegExp(`--color-${name}:\\s*#([0-9a-fA-F]{3,6})`).exec(css);
  if (!m) throw new Error(`jeton --color-${name} introuvable dans app/globals.css`);
  const hex = m[1];
  return hex.length === 3 ? hex.split("").map((c) => c + c).join("") : hex;
}

// Luminance relative WCAG 2.1 puis rapport de contraste.
function luminance(hex: string): number {
  const channels = [0, 2, 4].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function ratio(a: string, b: string): number {
  const [la, lb] = [luminance(a), luminance(b)];
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

describe("contraste des jetons de couleur", () => {
  const cases: [string, string][] = [
    ["link", "paper"],
    ["faint-text", "paper"],
    ["faint-text", "grey"],
    ["faint-dark", "black"],
    ["muted", "paper"],
    ["paper", "black"],
  ];
  for (const [fg, bg] of cases) {
    it(`${fg} sur ${bg} atteint 4,5:1`, () => {
      expect(ratio(token(fg), token(bg))).toBeGreaterThanOrEqual(4.5);
    });
  }
});
