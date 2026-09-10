import { ApiError, parseEnvelope } from "./api";

// Une session non posée (origine refusée, corps invalide, cookie rejeté...) doit se voir : sans ce
// contrôle, `fetch` rendait la main sans erreur et l'utilisateur repartait sur une page qui le croit
// déconnecté, sans jamais savoir pourquoi.
async function check(res: Response): Promise<void> {
  if (res.ok) return;
  try {
    await parseEnvelope<unknown>(res);
  } catch (err) {
    // parseEnvelope porte déjà le message de l'enveloppe du serveur ; s'il n'a rien trouvé de mieux
    // que le statusText HTTP, on lui substitue un texte lisible.
    if (err instanceof ApiError && err.message && err.message !== res.statusText) throw err;
  }
  throw new ApiError(res.status, "Session refusée");
}

export async function saveSession(token: string) {
  const res = await fetch("/api/session", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) });
  await check(res);
}

export async function clearSession() {
  const res = await fetch("/api/session", { method: "DELETE" });
  await check(res);
}
