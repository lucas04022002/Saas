import { api } from "./api";
import { formatTarif, type Tarif } from "./pricing";

/**
 * Le tarif à afficher, lu chez Stripe.
 *
 * Réservé au rendu serveur : la lecture passe par l'API, jamais par le
 * navigateur. Une panne ne doit pas laisser un trou à la place d'un prix, ni
 * faire tomber la page — on retombe alors sur le tarif de repli, et `reel`
 * vaut faux pour que l'appelant sache à quoi il a affaire.
 */
export async function lireTarif(): Promise<Tarif> {
  try {
    return formatTarif(await api.billing.plan());
  } catch {
    return formatTarif(null);
  }
}
