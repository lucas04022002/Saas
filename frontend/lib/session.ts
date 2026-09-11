import { cookies } from "next/headers";
import { api } from "./api";
import { ApiError } from "./envelope";
import type { User } from "./types";
export const TOKEN_COOKIE = "rp_token";
export async function getToken(): Promise<string | undefined> { return (await cookies()).get(TOKEN_COOKIE)?.value; }
export async function getUser(): Promise<User | null> {
  const token = await getToken();
  if (!token) return null;
  // L'API peut être injoignable (réseau, 500, timeout) : une page publique ne doit jamais planter avec
  // une erreur 500 juste parce que la session n'a pas pu être vérifiée. On dégrade en visiteur anonyme.
  try {
    return await api.me(token);
  } catch (e) {
    // 401 = jeton expiré ou révoqué : c'est un visiteur anonyme, pas une erreur à journaliser.
    if (e instanceof ApiError && e.status === 401) return null;
    console.warn("getUser: session non vérifiable", e instanceof Error ? e.message : e);
    return null;
  }
}
export const isPro = (u: User | null) => !!u && (u.subscription_plan === "PRO" || u.subscription_plan === "ELITE");
