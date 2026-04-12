const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface AuthUser {
  id: string;
  first_name: string;
  last_name: string | null;
  email: string;
  role: string;
  subscription_plan: string;
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);

  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      signal: controller.signal,
    });
  } catch (e: unknown) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error("Le serveur met trop de temps à répondre. Réessaie dans quelques secondes.");
    }
    throw new Error("Impossible de contacter le serveur. Vérifie ta connexion.");
  } finally {
    clearTimeout(timeout);
  }

  const json = await res.json();
  if (!res.ok) {
    throw new Error(json.message ?? json.detail ?? "Identifiants incorrects");
  }

  localStorage.setItem("rushplay_token", json.data.access_token);
  document.cookie = `rushplay_token=${json.data.access_token}; path=/; max-age=2592000; SameSite=Lax`;
  return json.data.user;
}

export async function signup(
  first_name: string,
  last_name: string,
  email: string,
  password: string
): Promise<AuthUser> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);

  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ first_name, last_name, email, password }),
      signal: controller.signal,
    });
  } catch (e: unknown) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error("Le serveur met trop de temps à répondre. Réessaie dans quelques secondes.");
    }
    throw new Error("Impossible de contacter le serveur. Vérifie ta connexion.");
  } finally {
    clearTimeout(timeout);
  }

  const json = await res.json();
  if (!res.ok) {
    const msg = json.message ?? json.detail;
    if (msg === "Email already exists") throw new Error("Cet email est déjà utilisé");
    throw new Error(msg ?? "Erreur lors de la création du compte");
  }

  localStorage.setItem("rushplay_token", json.data.access_token);
  document.cookie = `rushplay_token=${json.data.access_token}; path=/; max-age=2592000; SameSite=Lax`;
  return json.data.user;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("rushplay_token");
}

export function logout(): void {
  localStorage.removeItem("rushplay_token");
  document.cookie = "rushplay_token=; path=/; max-age=0";
}
