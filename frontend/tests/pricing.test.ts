import { describe, expect, it } from "vitest";
import { formatTarif, PRICE_MONTHLY_FALLBACK } from "@/lib/pricing";

const stripe = (o: Partial<Parameters<typeof formatTarif>[0]> = {}) => ({
  amount_cents: 900, currency: "eur", interval: "month", interval_count: 1, livemode: false, ...o,
});

describe("le tarif affiché vient de Stripe", () => {
  it("un montant rond ne montre pas de centimes", () => {
    const t = formatTarif(stripe());
    expect(t.montant).toBe("9");
    expect(t.devise).toBe("€");
    expect(t.periode).toBe("/ mois");
    expect(t.reel).toBe(true);
  });

  it("un montant avec centimes les affiche, à la française", () => {
    expect(formatTarif(stripe({ amount_cents: 950 })).montant).toBe("9,50");
    expect(formatTarif(stripe({ amount_cents: 1290 })).montant).toBe("12,90");
  });

  it("un changement de prix chez Stripe se voit sur la page", () => {
    // Le point de tout ce travail : le prix était écrit en dur, donc un tarif
    // passé à 12 € chez Stripe aurait laissé la page annoncer 9 €.
    expect(formatTarif(stripe({ amount_cents: 1200 })).phrase).toBe("12 € par mois");
  });

  it("un tarif trimestriel ne se fait pas passer pour un mensuel", () => {
    const t = formatTarif(stripe({ amount_cents: 2400, interval: "month", interval_count: 3 }));
    expect(t.periode).toBe("/ 3 mois");
    expect(t.periodeLongue).toBe("tous les 3 mois");
    expect(t.phrase).toBe("24 € tous les 3 mois");
  });

  it("un tarif annuel est nommé comme tel", () => {
    const t = formatTarif(stripe({ amount_cents: 9000, interval: "year" }));
    expect(t.periode).toBe("/ an");
    expect(t.phrase).toBe("90 € par an");
  });

  it("une autre devise garde son symbole", () => {
    expect(formatTarif(stripe({ currency: "gbp" })).devise).toBe("£");
  });

  it("Stripe injoignable : le repli s'affiche, et se déclare comme tel", () => {
    // Une page sans prix serait pire qu'un prix de repli. Mais `reel: false`
    // doit rester lisible par l'appelant : c'est ce qui distingue une panne
    // passagère d'un prix figé pour toujours dans le code.
    for (const absent of [null, undefined, stripe({ amount_cents: null })]) {
      const t = formatTarif(absent);
      expect(t.montant).toBe(String(PRICE_MONTHLY_FALLBACK));
      expect(t.reel).toBe(false);
    }
  });
});
