/**
 * Le prix de repli, utilisé quand Stripe est injoignable.
 *
 * Ce n'est PAS la source de vérité : le montant facturé est celui du tarif
 * Stripe désigné par `STRIPE_PRICE_ID`, et c'est lui que les pages affichent.
 * Cette constante ne sert qu'à ne pas laisser un trou à la place d'un prix le
 * jour où l'API ne répond pas. Si elle finit par diverger du tarif réel, c'est
 * seulement le temps d'une panne — au lieu d'être permanent, comme lorsque le
 * prix était écrit en dur dans la page.
 */
export const PRICE_MONTHLY_FALLBACK = 9;

export const PLAN_NAMES: Record<string, string> = {
  STARTER: "Gratuit",
  PRO: "Lecture complète",
  ELITE: "Lecture complète",
};

/** Ce que Stripe rend pour un tarif récurrent. */
export type PlanStripe = {
  amount_cents: number | null;
  currency: string;
  interval: string | null;
  interval_count: number;
  livemode: boolean;
  /** « inclusive » | « exclusive » | « unspecified » | null. */
  tax_behavior?: string | null;
};

export type Tarif = {
  /** Le montant seul, pour les gros chiffres : « 9 », « 9,50 ». */
  montant: string;
  /** Le symbole, ou le code pour une devise sans symbole connu. */
  devise: string;
  /** La périodicité telle qu'on l'écrit à côté du prix : « / mois ». */
  periode: string;
  /** La forme en toutes lettres, pour une phrase : « 9 € par mois ». */
  phrase: string;
  /** La périodicité seule, en toutes lettres : « par mois », « tous les 3 mois ». */
  periodeLongue: string;
  /** Faux quand le tarif vient du repli et non de Stripe. */
  reel: boolean;
  /**
   * Vrai quand le montant est bien celui qui sera prélevé.
   *
   * Faux si Stripe ajoute la taxe par-dessus (`tax_behavior: "exclusive"`) :
   * le site ne peut alors PAS afficher un prix TTC unique, puisque le taux
   * dépend du pays de l'acheteur. Écrire « TTC » dans ce cas revient à
   * annoncer un montant et en facturer un autre.
   */
  ttc: boolean;
};

const SYMBOLES: Record<string, string> = { EUR: "€", USD: "$", GBP: "£" };

const PERIODES: Record<string, { court: string; long: string }> = {
  day: { court: "jour", long: "par jour" },
  week: { court: "semaine", long: "par semaine" },
  month: { court: "mois", long: "par mois" },
  year: { court: "an", long: "par an" },
};

/** « 900 » → « 9 » ; « 950 » → « 9,50 ». Les centimes ne s'affichent que s'il y en a. */
function montantLisible(centimes: number): string {
  const unites = centimes / 100;
  const decimales = centimes % 100 === 0 ? 0 : 2;
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  }).format(unites);
}

/**
 * Met en forme le tarif Stripe, ou rend le repli.
 *
 * Fonction pure : elle ne va rien chercher, pour être testable sans réseau et
 * utilisable depuis n'importe quel composant.
 */
export function formatTarif(plan: PlanStripe | null | undefined): Tarif {
  if (!plan || plan.amount_cents === null || plan.amount_cents === undefined) {
    return {
      montant: String(PRICE_MONTHLY_FALLBACK),
      devise: "€",
      periode: "/ mois",
      phrase: `${PRICE_MONTHLY_FALLBACK} € par mois`,
      periodeLongue: "par mois",
      reel: false,
      ttc: true,
    };
  }

  const devise = SYMBOLES[plan.currency?.toUpperCase()] ?? plan.currency ?? "€";
  const montant = montantLisible(plan.amount_cents);
  const unite = PERIODES[plan.interval ?? "month"] ?? PERIODES.month;

  // Un tarif tous les 3 mois s'écrit « / 3 mois », pas « / mois » : afficher la
  // périodicité au singulier ferait passer un prix trimestriel pour mensuel.
  const multiple = (plan.interval_count ?? 1) > 1;
  const periode = multiple ? `/ ${plan.interval_count} ${unite.court}` : `/ ${unite.court}`;
  const periodeLongue = multiple ? `tous les ${plan.interval_count} ${unite.court}` : unite.long;
  const phrase = `${montant} ${devise} ${periodeLongue}`;

  // « unspecified » = aucune taxe paramétrée : le montant est bien celui payé.
  const ttc = plan.tax_behavior !== "exclusive";

  return { montant, devise, periode, phrase, periodeLongue, reel: true, ttc };
}
