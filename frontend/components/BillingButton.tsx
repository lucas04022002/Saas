"use client";

import { useState } from "react";

/**
 * Les deux boutons qui mènent chez Stripe : s'abonner, et gérer son abonnement.
 *
 * Ni l'un ni l'autre ne change quoi que ce soit dans notre base. Ils ouvrent
 * une page hébergée par Stripe, et c'est le webhook signé qui, plus tard,
 * décidera si le compte devient payant. Une redirection de navigateur peut
 * être fabriquée à la main ; un webhook signé, non.
 *
 * Aucune coordonnée bancaire ne transite par ce code : la carte est saisie
 * chez Stripe, sur son domaine.
 */
export function BillingButton({
  action,
  label,
  variant = "btn",
}: {
  action: "checkout" | "portal";
  label: string;
  variant?: string;
}) {
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function ouvrir() {
    setErreur(null);
    setChargement(true);
    try {
      const res = await fetch(`/api/billing/${action}`, { method: "POST" });
      const body = (await res.json()) as { data?: { url?: string }; message?: string };

      if (!res.ok || !body.data?.url) {
        // Le serveur nomme la cause quand il la connaît (Stripe refuse, tarif
        // introuvable, compte non activé...). L'écraser par « réessayez dans un
        // instant » invite à recommencer un geste qui ne peut pas aboutir, et
        // laisse le problème invisible des deux côtés de l'écran.
        setErreur(
          res.status === 503
            ? "Le paiement en ligne n'est pas encore ouvert."
            : res.status === 409
              ? "Vous êtes déjà abonné."
              : body.message ||
                "Impossible d'ouvrir la page de paiement. Réessayez dans un instant.",
        );
        return;
      }

      // `assign` et non `replace` : le retour en arrière ramène sur le site,
      // au lieu de piéger l'utilisateur sur la page de Stripe.
      window.location.assign(body.data.url);
    } catch {
      setErreur("Impossible de contacter le serveur.");
    } finally {
      setChargement(false);
    }
  }

  return (
    <>
      <button type="button" onClick={ouvrir} disabled={chargement} className={variant}>
        {chargement ? "Ouverture…" : label}
      </button>
      {erreur ? <output className="mt-3 block text-[14px] text-negative">{erreur}</output> : null}
    </>
  );
}
