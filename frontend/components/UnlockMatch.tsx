"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import type { Quota } from "@/lib/types";

/**
 * Le bouton qui dépense un crédit hebdomadaire.
 *
 * Il est déclenché par un clic, et seulement par un clic. La lecture d'un match
 * ne consomme rien : sans cela, le préchargement de Next.js au survol d'un lien
 * viderait le quota avant même que l'utilisateur ait décidé quoi que ce soit.
 *
 * Le compte à rebours est affiché AVANT l'action, pas après : on ne découvre
 * pas ce qu'on vient de dépenser.
 */
export function UnlockMatch({ matchId, quota }: { matchId: string; quota: Quota }) {
  const router = useRouter();
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  if (quota.plan === "ANONYMOUS") {
    return (
      <div className="hair py-8">
        <p className="text-[19px] font-semibold">Créez un compte gratuit pour voir ce match.</p>
        <p className="mt-2 max-w-[52ch] text-[15px] text-muted">
          Deux matchs par semaine, entièrement ouverts : le favori, sa probabilité et le score
          exact le plus probable.
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-4">
          <Link href="/inscription" className="btn">
            Créer un compte gratuit
          </Link>
          <Link href="/connexion" className="text-[14px] underline underline-offset-4">
            J&apos;ai déjà un compte
          </Link>
        </div>
      </div>
    );
  }

  const restants = quota.remaining ?? 0;

  if (restants <= 0) {
    return (
      <div className="hair py-8">
        <p className="text-[19px] font-semibold">Vous avez ouvert vos deux matchs de la semaine.</p>
        <p className="mt-2 max-w-[52ch] text-[15px] text-muted">
          Votre quota se recharge lundi. L&apos;abonnement ouvre tous les matchs, plus les écarts
          entre bookmakers, le mouvement des cotes et le comparateur.
        </p>
        <Link href="/tarifs" className="btn mt-5">
          Voir l&apos;abonnement
        </Link>
      </div>
    );
  }

  async function debloquer() {
    setErreur(null);
    setChargement(true);
    try {
      const res = await fetch(`/api/matches/${matchId}/unlock`, { method: "POST" });
      if (!res.ok) throw new ApiError(res.status, "Le déblocage a échoué.");
      // `refresh` relit la page côté serveur : le match revient déverrouillé,
      // avec ses vraies valeurs, sans qu'on ait à les recopier ici.
      router.refresh();
    } catch (e) {
      setErreur(
        e instanceof ApiError && e.status === 402
          ? "Vous avez ouvert vos matchs de la semaine. Le quota se recharge lundi."
          : "Le déblocage a échoué. Réessayez dans un instant.",
      );
    } finally {
      setChargement(false);
    }
  }

  return (
    <div className="hair py-8">
      <p className="text-[19px] font-semibold">Ce match est verrouillé.</p>
      <p className="mt-2 max-w-[52ch] text-[15px] text-muted">
        L&apos;ouvrir montre le favori, sa probabilité et le score exact le plus probable. Il
        restera ouvert pour vous : le relire ne coûtera rien.
      </p>

      {erreur ? (
        <output className="mt-4 block text-[14px] text-negative">{erreur}</output>
      ) : null}

      <div className="mt-5 flex flex-wrap items-center gap-4">
        <button type="button" onClick={debloquer} disabled={chargement} className="btn">
          {chargement ? "Ouverture…" : "Débloquer ce match"}
        </button>
        <span className="text-[14px] text-muted">
          Il vous reste {restants} match{restants > 1 ? "s" : ""} cette semaine.
        </span>
      </div>

      <p className="mt-4 text-[13px] text-muted">
        <Link href="/tarifs" className="underline underline-offset-4">
          L&apos;abonnement ouvre tous les matchs
        </Link>{" "}
        — sans quota, avec les écarts et le mouvement des cotes.
      </p>
    </div>
  );
}
