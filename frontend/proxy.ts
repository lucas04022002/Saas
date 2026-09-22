import { NextResponse, type NextRequest } from "next/server";
import { apiOrigin, buildCsp } from "@/lib/csp";

/**
 * Un nonce par requête, et la CSP qui va avec.
 *
 * Next lit le nonce dans l'en-tête `Content-Security-Policy` de la requête et l'applique à ses propres
 * scripts inline ; `x-nonce` le transmet au layout pour le script de thème. Convention Next 16 : ce
 * fichier remplace `middleware.ts`.
 */
export function proxy(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const csp = buildCsp(nonce, { apiOrigin: apiOrigin(), dev: process.env.NODE_ENV !== "production" });

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  // Tout sauf les fichiers statiques : ils n'exécutent rien et n'ont pas besoin d'un nonce.
  matcher: [{ source: "/((?!_next/static|_next/image|favicon.svg|apple-touch-icon.png|photos/|robots.txt|sitemap.xml).*)" }],
};
