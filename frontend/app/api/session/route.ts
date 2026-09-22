import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { originGuard } from "@/lib/route-utils";
const NAME = "rp_token";

/** Les secondes avant l'expiration du jeton, ou null s'il n'a pas de `exp` lisible. */
function secondesRestantes(token: string): number | null {
  try {
    const charge = JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString("utf8")) as { exp?: number };
    if (typeof charge.exp !== "number") return null;
    return Math.floor(charge.exp - Date.now() / 1000);
  } catch { return null; }
}
export async function POST(req: Request) {
  const guard = originGuard(req);
  if (guard) return guard;
  let body: { token?: string };
  try { body = (await req.json()) as { token?: string }; }
  catch { return NextResponse.json({ ok: false }, { status: 400 }); }
  const { token } = body;
  if (!token || typeof token !== "string") return NextResponse.json({ ok: false }, { status: 400 });
  // La durée du cookie est celle du jeton (audit du 22/09/2026, M3). Le cookie vivait 7 jours quand le
  // jeton expirait après JWT_EXPIRE_MINUTES : passé ce délai, chaque page voyait un 401 et l'utilisateur
  // se retrouvait « Se connecter » sans avoir rien fait, cookie toujours là. `exp` est lu sans vérifier
  // la signature : ce n'est pas une décision de sécurité (l'API vérifie à chaque appel), seulement une durée.
  const restant = secondesRestantes(token);
  if (restant === null || restant <= 0) return NextResponse.json({ ok: false }, { status: 400 });
  (await cookies()).set(NAME, token, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: restant });
  return NextResponse.json({ ok: true });
}
export async function DELETE(req: Request) {
  const guard = originGuard(req);
  if (guard) return guard;
  (await cookies()).delete(NAME);
  return NextResponse.json({ ok: true });
}
