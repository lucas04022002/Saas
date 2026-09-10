import { NextResponse } from "next/server";
import { ApiError } from "./envelope";
import { getToken } from "./session";

// Vérifie le cookie httpOnly côté serveur : renvoie le jeton, ou une réponse 401 toute prête si absent.
export async function requireToken(): Promise<string | NextResponse> {
  const token = await getToken();
  if (!token) return NextResponse.json({ success: false, message: "Non connecté" }, { status: 401 });
  return token;
}

// Traduit une ApiError (levée par lib/api.ts) en la même enveloppe que le backend ; toute autre erreur remonte.
export function errorEnvelope(e: unknown): NextResponse {
  if (e instanceof ApiError) return NextResponse.json({ success: false, message: e.message }, { status: e.status });
  throw e;
}

// Garde CSRF : refuse toute requête mutante qui ne vient pas manifestement du même site. `Sec-Fetch-Site`
// (posé par le navigateur, jamais falsifiable en JS) est la vérification principale ; `Origin` sert de
// repli pour les clients qui ne l'envoient pas. Renvoie null si la requête peut continuer.
export function originGuard(req: Request): NextResponse | null {
  const site = req.headers.get("sec-fetch-site");
  if (site === "same-origin" || site === "none") return null;
  const origin = req.headers.get("origin");
  // Comparaison sur l'hôte seul, pas sur l'origine complète : derrière un reverse proxy qui termine le
  // TLS, la requête vue par Next.js est en `http` alors que le navigateur annonce `Origin: https://…`.
  // Comparer les schémas refuserait alors des requêtes parfaitement légitimes (403 en production).
  // L'hôte, lui, reste discriminant : c'est bien ce qui distingue notre site d'un site tiers.
  if (origin) {
    try { if (new URL(origin).host === new URL(req.url).host) return null; }
    catch { /* `Origin` illisible (« null », valeur bricolée…) : on refuse. */ }
  }
  return NextResponse.json({ success: false, message: "Origine refusée" }, { status: 403 });
}
