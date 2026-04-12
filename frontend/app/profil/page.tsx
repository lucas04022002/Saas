"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "../../components/sections/navbar/default";
import FooterSection from "../../components/sections/footer/default";
import { getToken, logout } from "../../lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface UserData {
  id: string;
  first_name: string;
  email: string;
  role: string;
  subscription_plan: string;
}

const PLAN_LABELS: Record<string, string> = {
  STARTER: "Starter",
  PRO: "Pro",
  ELITE: "Elite",
};

const PLAN_COLORS: Record<string, string> = {
  STARTER: "bg-slate-700 text-slate-200",
  PRO: "bg-[#c8f000]/20 text-[#c8f000] border border-[#c8f000]/30",
  ELITE: "bg-purple-500/20 text-purple-300 border border-purple-500/30",
};

export default function ProfilPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }

    fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((json) => {
        if (json?.data) setUser(json.data);
        else router.push("/login");
      })
      .catch(() => router.push("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <div className="min-h-screen bg-[#10131a] text-white">
      <Navbar activePath="/profil" />
      <main className="pt-24 pb-16">
        <div className="max-w-xl mx-auto px-6">
          <h1
            className="text-3xl font-black text-white mb-8"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Mon Profil
          </h1>

          {loading && (
            <div className="text-slate-500 text-sm animate-pulse">Chargement…</div>
          )}

          {!loading && user && (
            <div className="space-y-4">
              {/* Info card */}
              <div className="bg-[#1d2027] rounded-2xl border border-[#454933]/15 p-6 space-y-5">
                {/* Avatar + name */}
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-full bg-[#c8f000]/10 border border-[#c8f000]/20 flex items-center justify-center">
                    <span
                      className="text-2xl font-black text-[#c8f000]"
                      style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                    >
                      {user.first_name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p
                      className="text-xl font-bold text-white"
                      style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                    >
                      {user.first_name}
                    </p>
                    <p className="text-sm text-slate-400">{user.email}</p>
                  </div>
                </div>

                <div className="h-px bg-[#454933]/20" />

                {/* Plan */}
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-1">
                      Abonnement
                    </p>
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-sm font-bold ${PLAN_COLORS[user.subscription_plan] ?? PLAN_COLORS.STARTER}`}
                    >
                      {PLAN_LABELS[user.subscription_plan] ?? user.subscription_plan}
                    </span>
                  </div>
                  <a
                    href="/tarifs"
                    className="bg-[#c8f000] text-[#2a3400] px-4 py-2 rounded-xl text-sm font-extrabold hover:brightness-110 transition-all"
                    style={{ fontFamily: "var(--font-heading, sans-serif)" }}
                  >
                    {user.subscription_plan === "STARTER" ? "Passer Pro" : "Gérer"}
                  </a>
                </div>
              </div>

              {/* Logout */}
              <button
                onClick={handleLogout}
                className="w-full py-3 rounded-xl border border-[#f87171]/30 text-[#f87171] text-sm font-bold hover:bg-[#f87171]/10 transition-all"
              >
                Se déconnecter
              </button>
            </div>
          )}
        </div>
      </main>
      <FooterSection />
    </div>
  );
}
