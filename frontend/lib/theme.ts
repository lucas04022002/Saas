// Trois positions : « système » (aucun attribut, la media query décide), « clair » et « sombre »
// (attribut explicite sur <html>, qui gagne sur le système). Le choix vit dans localStorage.
export type ThemeChoice = "system" | "light" | "dark";

export const THEME_KEY = "rp-theme";
export const THEME_ATTR = "data-theme";

export const THEME_OPTIONS: { value: ThemeChoice; label: string }[] = [
  { value: "system", label: "Système" },
  { value: "light", label: "Clair" },
  { value: "dark", label: "Sombre" },
];

function isExplicit(v: unknown): v is "light" | "dark" {
  return v === "light" || v === "dark";
}

// Joué en <head>, pendant l'analyse du HTML, donc avant la première peinture : pas de flash blanc.
// Volontairement sans dépendance ni sucre syntaxique — il part tel quel dans le HTML.
export const THEME_SCRIPT =
  `(function(){try{var t=window.localStorage.getItem(${JSON.stringify(THEME_KEY)});` +
  `var e=document.documentElement;` +
  `if(t==="light"||t==="dark")e.setAttribute(${JSON.stringify(THEME_ATTR)},t);` +
  `else e.removeAttribute(${JSON.stringify(THEME_ATTR)});` +
  `}catch(e){}})()`;

export function readTheme(): ThemeChoice {
  try {
    const v = window.localStorage.getItem(THEME_KEY);
    return isExplicit(v) ? v : "system";
  } catch {
    // Cookies/stockage bloqués : on retombe sur le système, jamais sur une erreur.
    return "system";
  }
}

export function storeTheme(choice: ThemeChoice): void {
  try {
    if (choice === "system") window.localStorage.removeItem(THEME_KEY);
    else window.localStorage.setItem(THEME_KEY, choice);
  } catch {
    /* stockage indisponible : le choix ne survivra pas au rechargement, tant pis */
  }
}

export function applyTheme(choice: ThemeChoice): void {
  const el = document.documentElement;
  if (choice === "system") el.removeAttribute(THEME_ATTR);
  else el.setAttribute(THEME_ATTR, choice);
}

// Petit magasin externe : le sélecteur le lit avec useSyncExternalStore, qui sait rendre
// « système » côté serveur puis rattraper le choix réel une fois hydraté, sans divergence.
const listeners = new Set<() => void>();

export function subscribeTheme(onChange: () => void): () => void {
  listeners.add(onChange);
  // Un autre onglet qui change de thème doit se voir ici aussi.
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onChange);
  };
}

export function setTheme(choice: ThemeChoice): void {
  storeTheme(choice);
  applyTheme(choice);
  for (const l of listeners) l();
}
