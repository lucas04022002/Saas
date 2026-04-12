"use client";

import { useRouter } from "next/navigation";
import { logout } from "../../lib/auth";

interface UserData {
  id: string;
  first_name: string;
  last_name: string | null;
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

export default function ProfilClient({ user }: { user: UserData }) {
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <main className="pt-24 pb-16">
      <div className="max-w-xl mx-auto px-6">
        <h1
          className="text-3xl font-black text-white mb-8"
          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
        >
          Mon Profil
        </h1>

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
                  {user.first_name}{user.last_name ? ` ${user.last_name}` : ""}
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
      </div>
    </main>
  );
}
