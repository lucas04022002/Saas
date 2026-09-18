import { NextResponse } from "next/server";
import { api } from "@/lib/api";
import { errorEnvelope, originGuard, requireToken } from "@/lib/route-utils";

/**
 * Relais vers Stripe : ouverture d'un paiement, ou du portail de facturation.
 *
 * Le jeton vit dans un cookie httpOnly — un composant client ne peut pas le
 * lire, et ne doit pas. `originGuard` est indispensable : sans lui, un autre
 * site pourrait déclencher une session de paiement au nom d'un visiteur
 * connecté.
 *
 * Seules deux actions sont acceptées. Passer le segment d'URL tel quel à
 * l'API laisserait n'importe qui appeler n'importe quelle route de facturation.
 */
const ACTIONS = new Set(["checkout", "portal"]);

export async function POST(req: Request, ctx: { params: Promise<{ action: string }> }) {
  const guard = originGuard(req);
  if (guard) return guard;

  const token = await requireToken();
  if (token instanceof NextResponse) return token;

  const { action } = await ctx.params;
  if (!ACTIONS.has(action)) {
    return NextResponse.json({ success: false, message: "Action inconnue", data: null }, { status: 404 });
  }

  try {
    const data =
      action === "checkout" ? await api.billing.checkout(token) : await api.billing.portal(token);
    return NextResponse.json({ success: true, message: "", data });
  } catch (e) {
    return errorEnvelope(e);
  }
}
