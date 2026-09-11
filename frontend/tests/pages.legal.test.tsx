import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LEGAL, TO_FILL } from "@/lib/legal";

describe("pages légales", () => {
  it("mentions légales : rend le titre et les sections obligatoires", async () => {
    const Page = (await import("@/app/mentions-legales/page")).default;
    render(<Page />);
    expect(screen.getByRole("heading", { level: 1, name: "Mentions légales." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hébergeur" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Données personnelles" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Avertissement jeux d'argent" })).toBeInTheDocument();
    // L'hébergeur est connu : il doit apparaître en clair, pas en "À COMPLÉTER".
    expect(screen.getByText(new RegExp(LEGAL.hostName))).toBeInTheDocument();
    expect(screen.getByText(/09 74 75 13 13/)).toBeInTheDocument();
  });

  it("CGU : rend le titre et les sections obligatoires", async () => {
    const Page = (await import("@/app/cgu/page")).default;
    render(<Page />);
    expect(screen.getByRole("heading", { level: 1, name: "Conditions d'utilisation." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Offres et prix" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Droit de rétractation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Résiliation" })).toBeInTheDocument();
    expect(screen.getByText(/9 € TTC par mois/)).toBeInTheDocument();
  });
});

// Garde-fou de mise en ligne : lib/legal.ts contient volontairement des champs "À COMPLÉTER"
// tant que Lucas n'a pas renseigné son identité d'éditeur (nom, adresse, SIREN...). Ce test
// vérifie qu'aucun champ ne vaut plus TO_FILL, mais UNIQUEMENT quand la variable d'environnement
// CI_STRICT_LEGAL vaut "1" : la CI actuelle ne la définit pas, donc ce test reste vert même avec
// des champs vides. Pour activer le contrôle strict au lancement commercial du site, une fois
// lib/legal.ts entièrement renseigné : ajouter `CI_STRICT_LEGAL: "1"` dans le bloc `env:` du job
// `frontend-checks` de .github/workflows/quality-checks.yml (ou l'exporter avant `npm test`).
describe("garde-fou avant mise en ligne (CI_STRICT_LEGAL)", () => {
  it("aucun champ de lib/legal.ts ne reste à compléter, en build strict", () => {
    const strict = process.env.CI_STRICT_LEGAL === "1";
    const incomplete = Object.entries(LEGAL)
      .filter(([, value]) => value === TO_FILL)
      .map(([key]) => key);
    if (!strict) {
      // CI non stricte : on documente juste l'état actuel, sans faire échouer le test.
      expect(Array.isArray(incomplete)).toBe(true);
      return;
    }
    expect(incomplete, `champs encore "À COMPLÉTER" dans lib/legal.ts : ${incomplete.join(", ")}`).toEqual([]);
  });
});
