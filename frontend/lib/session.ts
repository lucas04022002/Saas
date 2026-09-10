import { cookies } from "next/headers";
import { api, ApiError } from "./api";
import type { User } from "./types";
export const TOKEN_COOKIE = "rp_token";
export async function getToken(): Promise<string | undefined> { return (await cookies()).get(TOKEN_COOKIE)?.value; }
export async function getUser(): Promise<User | null> {
  const token = await getToken();
  if (!token) return null;
  try { return await api.me(token); } catch (e) { if (e instanceof ApiError) return null; throw e; }
}
export const isPro = (u: User | null) => !!u && (u.subscription_plan === "PRO" || u.subscription_plan === "ELITE");
