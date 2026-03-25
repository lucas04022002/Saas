"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getToken, logout } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const planLabels: Record<string, { label: string; signals: string }> = {
  STARTER: { label: "Starter", signals: "3 signaux / jour" },
  PRO:     { label: "Pro",     signals: "Signaux illimités" },
  ELITE:   { label: "Elite",  signals: "Tout inclus" },
};

export default function UserPlan() {
  const [plan, setPlan] = useState<string>("STARTER");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) { setLoaded(true); return; }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then((r) => r.json())
      .then((json) => {
        if (json?.data?.subscription_plan) setPlan(json.data.subscription_plan);
      })
      .catch(() => {})
      .finally(() => {
        clearTimeout(timeout);
        setLoaded(true);
      });
  }, []);

  const info = planLabels[plan] ?? planLabels.STARTER;
  const isPro = plan === "PRO" || plan === "ELITE";

  function handleLogout() {
    logout();
    window.location.href = "/login";
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="rounded-xl border border-[#1E2D42] bg-[#0E1828] p-4 flex flex-col gap-3">
        <div className="text-xs text-[#7A8FA8] font-medium uppercase tracking-wide">Plan actuel</div>
        <div className="font-bold text-[#DDD5C4]">
          {loaded ? info.label : <span className="opacity-40">…</span>}
        </div>
        <div className="text-xs text-[#7A8FA8]">{info.signals}</div>
        {loaded && !isPro && (
          <Link
            href="/#pricing"
            className="mt-1 inline-flex items-center justify-center rounded-md px-3 py-1.5 text-xs font-semibold"
            style={{ background: "#C8F000", color: "#06090F" }}
          >
            Passer Pro
          </Link>
        )}
      </div>
      <button
        onClick={handleLogout}
        className="text-xs text-[#7A8FA8] hover:text-[#f87171] transition-colors text-left px-1"
      >
        Déconnexion
      </button>
    </div>
  );
}
