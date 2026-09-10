"use client";
import { useRouter } from "next/navigation";
import { clearSession } from "@/lib/client-session";
export function LogoutButton() {
  const router = useRouter();
  return <button className="btn-ghost mt-8" onClick={async () => { await clearSession(); router.push("/"); router.refresh(); }}>Se déconnecter</button>;
}
