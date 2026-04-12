export const dynamic = "force-dynamic";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Navbar from "../../components/sections/navbar/default";
import FooterSection from "../../components/sections/footer/default";
import ProfilClient from "./profil-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default async function ProfilPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("rushplay_token")?.value;

  if (!token) redirect("/login");

  let user = null;
  try {
    const res = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    const json = await res.json();
    user = json?.data ?? null;
  } catch {
    redirect("/login");
  }

  if (!user) redirect("/login");

  return (
    <div className="min-h-screen bg-[#10131a] text-white">
      <Navbar activePath="/profil" />
      <ProfilClient user={user} />
      <FooterSection />
    </div>
  );
}
