"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError } from "@/lib/api";
import { clearSession } from "@/lib/client-session";

/**
 * Quitter sa session. Deux emplacements, une seule logique.
 *
 * `page` : le bouton pleine taille, au bas de la page Compte.
 * `nav`  : le même geste depuis n'importe quelle page. Sans lui, se déconnecter
 *          imposait de retrouver d'abord la page Compte — ce que personne ne
 *          fait sur un ordinateur partagé, où c'est justement le geste pressé.
 *
 * L'échec ne redirige pas. Renvoyer vers l'accueil alors que le cookie est
 * toujours posé donnerait l'illusion d'être déconnecté, ce qui est pire que de
 * ne pas l'être : on s'éloigne de l'écran en croyant la session fermée.
 */
export function LogoutButton({ variant = "page" }: { variant?: "page" | "nav" }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const enNav = variant === "nav";

  async function logout() {
    try {
      await clearSession();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Déconnexion impossible. Réessaie dans un instant.");
      return;
    }
    setError(null);
    router.push("/");
    router.refresh();
  }

  return (
    <>
      <button
        type="button"
        onClick={logout}
        className={enNav ? "shrink-0 cursor-pointer text-nav-muted hover:text-paper" : "btn-ghost mt-8"}
      >
        Se déconnecter
      </button>
      {error && (
        <span role="alert" className={enNav ? "shrink-0 text-paper" : "mt-4 block text-[14px] font-medium"}>
          {error}
        </span>
      )}
    </>
  );
}
