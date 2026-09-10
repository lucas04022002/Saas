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
