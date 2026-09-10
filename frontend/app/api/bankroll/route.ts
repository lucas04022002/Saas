import { NextResponse } from "next/server";
import { api } from "@/lib/api";
import { errorEnvelope, originGuard, requireToken } from "@/lib/route-utils";

type BetInput = { match_id: string; outcome: string; bookmaker: string; odds: number; stake: number };

export async function GET() {
  const token = await requireToken();
  if (token instanceof NextResponse) return token;
  try {
    const data = await api.bankroll.list(token);
    return NextResponse.json({ success: true, message: "", data });
  } catch (e) {
    return errorEnvelope(e);
  }
}

export async function POST(req: Request) {
  const guard = originGuard(req);
  if (guard) return guard;
  const token = await requireToken();
  if (token instanceof NextResponse) return token;
  // Même garde que app/api/session/route.ts : un corps non-JSON fait lever req.json(), qui remonterait
  // en 500 si on ne l'attrapait pas ici.
  let body: BetInput;
  try { body = (await req.json()) as BetInput; }
  catch { return NextResponse.json({ success: false, message: "Corps de requête invalide" }, { status: 400 }); }
  try {
    const data = await api.bankroll.create(token, body);
    // Le backend répond 201 sur la création d'un pari : le proxy garde le même statut.
    return NextResponse.json({ success: true, message: "", data }, { status: 201 });
  } catch (e) {
    return errorEnvelope(e);
  }
}
