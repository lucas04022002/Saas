"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { saveSession } from "@/lib/client-session";

const field = "mt-2 w-full border-0 border-b border-ink bg-transparent py-2 text-[17px] font-medium outline-none focus:border-b-2";
const label = "block text-[12px] font-semibold uppercase tracking-[0.04em] text-muted";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const [f, setF] = useState({ first_name: "", email: "", password: "", birth_date: "", adult: false });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const signup = mode === "signup";
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null);
    try {
      const data = signup ? await api.signup({ first_name: f.first_name, email: f.email, password: f.password, birth_date: f.birth_date }) : await api.login(f.email, f.password);
      await saveSession(data.access_token);
      router.push("/matchs"); router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de joindre le service. Réessaie dans un instant.");
    } finally { setBusy(false); }
  }

  return (
    <form onSubmit={submit} className="max-w-[420px]">
      {signup && <div className="mt-6"><label className={label} htmlFor="first_name">Prénom</label><input id="first_name" className={field} value={f.first_name} onChange={set("first_name")} required minLength={2} autoComplete="given-name" /></div>}
      <div className="mt-6"><label className={label} htmlFor="email">E-mail</label><input id="email" type="email" className={field} value={f.email} onChange={set("email")} required autoComplete="email" /></div>
      <div className="mt-6"><label className={label} htmlFor="password">Mot de passe</label><input id="password" type="password" className={field} value={f.password} onChange={set("password")} required minLength={8} autoComplete={signup ? "new-password" : "current-password"} /></div>
      {signup && <>
        <div className="mt-6"><label className={label} htmlFor="birth_date">Date de naissance</label><input id="birth_date" type="date" className={field} value={f.birth_date} onChange={set("birth_date")} required /></div>
        <label className="mt-6 flex items-start gap-3 text-[14px]"><input type="checkbox" checked={f.adult} onChange={set("adult")} className="mt-1" /><span>J&apos;ai 18 ans ou plus. Les paris sportifs comportent des risques : endettement, dépendance… Appelez le 09 74 75 13 13.</span></label>
      </>}
      {error && <p role="alert" className="mt-5 text-[14px] font-medium">{error}</p>}
      <button type="submit" disabled={busy || (signup && !f.adult)} className="btn mt-8 disabled:opacity-40">{signup ? "Créer mon compte" : "Se connecter"}</button>
      <p className="mt-6 text-[14px] text-muted">{signup ? <>Déjà un compte ? <Link href="/connexion" className="text-link">Se connecter</Link></> : <>Pas encore de compte ? <Link href="/inscription" className="text-link">Créer un compte</Link></>}</p>
    </form>
  );
}
