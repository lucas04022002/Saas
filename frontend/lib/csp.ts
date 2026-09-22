/**
 * La Content-Security-Policy, comme une fonction pure : testable sans navigateur.
 *
 * Audit du 22/09/2026 (M2) : le site n'en avait pas. Le jeton vit en cookie httpOnly, ce qui borne
 * l'enjeu d'un XSS, mais un script injecté pourrait encore appeler les Route Handlers au nom de
 * l'utilisateur. Les scripts ne passent que par le nonce de la requête (posé par `proxy.ts`), et le
 * navigateur ne peut joindre que le site et l'API.
 *
 * `'unsafe-inline'` sur les styles : Next et un composant posent des attributs `style` ; le risque
 * d'un style injecté est sans commune mesure avec celui d'un script.
 */
export function buildCsp(nonce: string, { apiOrigin, dev }: { apiOrigin: string; dev: boolean }): string {
  const script = ["'self'", `'nonce-${nonce}'`, "'strict-dynamic'", ...(dev ? ["'unsafe-eval'"] : [])];
  const connect = ["'self'", apiOrigin, ...(dev ? ["ws:", "wss:"] : [])];
  return [
    `default-src 'self'`,
    `script-src ${script.join(" ")}`,
    `style-src 'self' 'unsafe-inline'`,
    `img-src 'self' data:`,
    `font-src 'self'`,
    `connect-src ${connect.join(" ")}`,
    `frame-ancestors 'none'`,
    `base-uri 'self'`,
    `form-action 'self'`,
    `object-src 'none'`,
    ...(dev ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");
}

/** L'origine de l'API telle que le navigateur la joindra (même variable que le client). */
export function apiOrigin(): string {
  try { return new URL(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").origin; }
  catch { return "http://localhost:8000"; }
}
