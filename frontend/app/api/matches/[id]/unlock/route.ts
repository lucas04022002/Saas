import { NextResponse } from "next/server";
import { api } from "@/lib/api";
import { errorEnvelope, originGuard, requireToken } from "@/lib/route-utils";

/**
 * Dépense un crédit hebdomadaire pour ouvrir un match.
 *
 * Ce relais existe parce que le jeton vit dans un cookie httpOnly : un
 * composant client ne peut pas le lire, et ne doit pas pouvoir le lire. Il
 * appelle donc cette route, qui ajoute le jeton côté serveur.
 *
 * `originGuard` est indispensable ici : sans lui, un autre site pourrait faire
 * dépenser les crédits d'un visiteur connecté à son insu.
 */
export async function POST(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const guard = originGuard(_req);
  if (guard) return guard;

  const token = await requireToken();
  if (token instanceof NextResponse) return token;

  const { id } = await ctx.params;

  try {
    const data = await api.unlockMatch(id, token);
    return NextResponse.json({ success: true, message: "", data });
  } catch (e) {
    return errorEnvelope(e);
  }
}
