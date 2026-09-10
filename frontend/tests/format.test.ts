import { describe, expect, it } from "vitest";
import { formatDateFr, formatGap, formatOdds, formatPct, formatSigned, sinceHours } from "@/lib/format";
describe("format", () => {
  it("pourcentage arrondi avec espace insécable", () => expect(formatPct(0.5821)).toBe("58 %"));
  it("cote avec virgule", () => expect(formatOdds(1.78)).toBe("1,78"));
  it("écart signé", () => { expect(formatGap(0.032)).toBe("+3,2 %"); expect(formatGap(-0.1)).toBe("−10,0 %"); });
  it("signé avec unité", () => expect(formatSigned(3.1, " pts")).toBe("+3,1 pts"));
  it("date française", () => expect(formatDateFr("2026-09-13T15:15:00Z")).toBe("dimanche 13 septembre, 17:15"));
  it("heures écoulées", () => expect(sinceHours("2026-09-13T03:00:00Z", new Date("2026-09-13T12:00:00Z"))).toBe(9));
});
