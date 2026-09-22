import { describe, expect, it } from "vitest";
import { COMPETITIONS, COMPETITION_GROUPS, COMPETITION_ORDER } from "@/lib/types";

describe("catalogue des compétitions côté site", () => {
  it("l'ordre d'affichage couvre exactement le catalogue : rien de compté sans être montré", () => {
    // La page Matchs compte les matchs par groupe ORDER : une compétition présente dans COMPETITIONS
    // mais absente de l'ordre serait renvoyée par l'API, comptée nulle part et jamais affichée.
    expect([...COMPETITION_ORDER].sort()).toEqual(Object.keys(COMPETITIONS).sort());
    expect(new Set(COMPETITION_ORDER).size).toBe(COMPETITION_ORDER.length);
  });

  it("les groupes portent les codes attendus", () => {
    const parLibelle = Object.fromEntries(COMPETITION_GROUPS.map(([label, entries]) => [label, entries.map(([code]) => code)]));
    expect(parLibelle["Top 5"]).toEqual(["F1", "E0", "SP1", "D1", "I1"]);
    expect(parLibelle["Coupes d'Europe et sélections"]).toEqual(["CL", "EL", "NL"]);
    expect(parLibelle["Autres championnats"]).toEqual(["E1", "F2", "SP2", "D2", "I2", "N1", "P1", "B1", "T1", "G1", "SC0"]);
  });

  it("chaque nouvelle compétition a un libellé lisible", () => {
    expect(COMPETITIONS.NL).toBe("Ligue des Nations");
    expect(COMPETITIONS.E1).toBe("Championship");
    expect(COMPETITIONS.SC0).toBe("Premiership écossaise");
    expect(COMPETITIONS.T1).toBe("Süper Lig");
  });
});
