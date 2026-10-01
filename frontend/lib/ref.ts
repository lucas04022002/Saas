// Mesure des réseaux (01/10/2026) : le lien posé en bio est `rushplay.fr/?ref=tiktok` (ou insta…).
// À l'arrivée : on signale UNE visite au serveur (un compteur par jour et par réseau, rien d'autre),
// on garde le nom du réseau 30 jours dans ce navigateur, et on retire `?ref=` de l'adresse pour qu'un
// rechargement ou un lien copié ne compte pas une deuxième fois. À l'inscription, le formulaire joint
// ce nom au compte : c'est ce qui permet de savoir quel réseau amène des inscrits et des abonnés.
import { api } from "./api";

export const SOURCES = ["tiktok", "insta", "youtube", "facebook", "snap", "x"] as const;
export type Source = (typeof SOURCES)[number];
export const REF_KEY = "rp_ref";
export const REF_DUREE_MS = 30 * 24 * 3600 * 1000;

export function sourceValide(v: string | null | undefined): Source | null {
  const s = (v ?? "").trim().toLowerCase();
  return (SOURCES as readonly string[]).includes(s) ? (s as Source) : null;
}

// stockage indisponible (navigation privée stricte, stockage bloqué) : la mesure se tait, le site marche
function stockage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** À appeler une fois par chargement de page. Rend la source retenue, ou null. */
export function captureRef(envoyer: (s: Source) => Promise<unknown> = api.visit): Source | null {
  const params = new URLSearchParams(window.location.search);
  if (!params.has("ref")) return null;
  const source = sourceValide(params.get("ref"));
  params.delete("ref");
  const q = params.toString();
  window.history.replaceState(window.history.state, "", `${window.location.pathname}${q ? `?${q}` : ""}${window.location.hash}`);
  if (!source) return null;
  try {
    stockage()?.setItem(REF_KEY, JSON.stringify({ s: source, t: Date.now() }));
  } catch {
    /* plein ou refusé : on compte quand même la visite */
  }
  envoyer(source).catch(() => {});
  return source;
}

/** Le réseau d'arrivée encore valable (moins de 30 jours), sinon null — et l'entrée périmée est effacée. */
export function sourceGardee(maintenant = Date.now()): Source | null {
  const st = stockage();
  try {
    const brut = st?.getItem(REF_KEY);
    if (!brut) return null;
    const { s, t } = JSON.parse(brut) as { s?: string; t?: number };
    if (typeof t !== "number" || maintenant - t > REF_DUREE_MS) {
      st?.removeItem(REF_KEY);
      return null;
    }
    return sourceValide(s);
  } catch {
    return null;
  }
}
