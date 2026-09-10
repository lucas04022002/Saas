// Enveloppe de réponse commune au backend et aux Route Handlers. Vit dans son propre module pour que
// le code serveur (lib/api.ts), le code navigateur (lib/client-api.ts, lib/client-session.ts) et les
// routes partagent exactement le même déballage — et le même type d'erreur.

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); this.name = "ApiError"; }
}

type Envelope<T> = { success: boolean; message: string; data: T };

export async function parseEnvelope<T>(res: Response): Promise<T> {
  let body: unknown = null;
  try { body = await res.json(); } catch { body = null; }
  if (!res.ok) {
    const b = body as { message?: string; detail?: unknown };
    let message = b?.message ?? res.statusText;
    if (Array.isArray(b?.detail) && b.detail.length) {
      const msg = String((b.detail[0] as { msg?: string }).msg ?? "");
      message = msg.replace(/^Value error, /, "");
    } else if (typeof b?.detail === "string") message = b.detail;
    throw new ApiError(res.status, message);
  }
  return (body as Envelope<T>).data;
}
