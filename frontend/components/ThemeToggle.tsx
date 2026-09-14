"use client";
import { useEffect, useSyncExternalStore } from "react";
import { applyTheme, readTheme, setTheme, subscribeTheme, THEME_OPTIONS, type ThemeChoice } from "@/lib/theme";

const SERVER_SNAPSHOT = (): ThemeChoice => "system";

export function ThemeToggle() {
  // Le serveur ne connaît pas le choix : il rend « Système », et useSyncExternalStore reprend
  // la vraie valeur du stockage une fois l'hydratation faite, sans avertissement de divergence.
  // L'affichage de la page, lui, est déjà juste : le script inline du <head> a posé data-theme
  // avant la première peinture.
  const choice = useSyncExternalStore(subscribeTheme, readTheme, SERVER_SNAPSHOT);

  // Filet : en développement, le remontage du mode strict de React remet <html> aux seuls
  // attributs venus du JSX et efface celui posé par le script inline. No-op en production.
  useEffect(() => {
    applyTheme(choice);
  }, [choice]);

  return (
    <div role="group" aria-label="Thème" className="flex rounded-[10px] bg-segment p-[3px]">
      {THEME_OPTIONS.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={choice === o.value}
          onClick={() => setTheme(o.value)}
          className={`rounded-lg px-3 py-1 text-[12px] font-semibold text-ink ${choice === o.value ? "bg-segment-on shadow-sm" : ""}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
