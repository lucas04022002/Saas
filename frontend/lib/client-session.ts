export async function saveSession(token: string) { await fetch("/api/session", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) }); }
export async function clearSession() { await fetch("/api/session", { method: "DELETE" }); }
