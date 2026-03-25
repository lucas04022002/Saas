"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getToken } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const planLabels: Record<string, { label: string; signals: string }> = {
  STARTER: { label: "Starter", signals: "3 signaux / jour" },
  PRO:     { label: "Pro",     signals: "Signaux illimités" },
  ELITE:   { label: "Elite",   signals: "Tout inclus" },
};

export default function UserPlan() {
  const [plan, setPlan] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((json) => setPlan(json?.data?.subscription_plan ?? null))
      .catch(() => {});
  }, []);

  const info = planLabels[plan ?? "STARTER"];

  return (
    <div className="rounded-xl border border-[#1E2D42] bg-[#0E1828] p-4 flex flex-col gap-3">
      <div className="text-xs text-[#7A8FA8] font-medium uppercase tracking-wide">Plan actuel</div>
      <div className="font-bold text-[#DDD5C4]">{info.label}</div>
      <div className="text-xs text-[#7A8FA8]">{info.signals}</div>
      {plan !== "PRO" && plan !== "ELITE" && (
        <Link
          href="/#pricing"
          className="mt-1 inline-flex items-center justify-center rounded-md px-3 py-1.5 text-xs font-semibold transition-colors"
          style={{ background: "#C8F000", color: "#06090F" }}
        >
          Passer Pro
        </Link>
      )}
    </div>
  );
}
