import { NextResponse } from "next/server";
import { ApiError } from "./api";
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
  if (origin && origin === new URL(req.url).origin) return null;
  return NextResponse.json({ success: false, message: "Origine refusée" }, { status: 403 });
}
