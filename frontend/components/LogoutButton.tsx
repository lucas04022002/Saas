"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError } from "@/lib/api";
import { clearSession } from "@/lib/client-session";

export function LogoutButton() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  async function logout() {
    try {
      await clearSession();
    } catch (err) {
      // Le cookie est toujours là : rediriger donnerait l'illusion d'une déconnexion réussie alors
      // que la session reste ouverte. On reste sur place et on le dit, à l'écran et aux lecteurs d'écran.
      setError(err instanceof ApiError ? err.message : "Déconnexion impossible. Réessaie dans un instant.");
      return;
    }
    setError(null);
    router.push("/");
    router.refresh();
  }

  return (
    <>
      <button className="btn-ghost mt-8" onClick={logout}>Se déconnecter</button>
      {error && <p role="alert" className="mt-4 text-[14px] font-medium">{error}</p>}
    </>
  );
}
