const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ApiMatch {
  id: string;
  home_team: string;
  away_team: string;
  league: string;
  country: string;
  kickoff_at: string;
  status: string;
  last_analyzed_at: string | null;
  confidence_score: number | null;
  recommended_bet: string | null;
  bookmaker_odds: number | null;
  value_percent: number | null;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | null;
}

export interface ApiAnalysis {
  match_id: string;
  home_team: string;
  away_team: string;
  league?: string;
  confidence_score: number;
  recommended_bet: string;
  bookmaker_odds: number;
  value_percent: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  ai_explanation: string;
  created_at: string;
}

export async function fetchMatches(params?: {
  page?: number;
  limit?: number;
  sort_by?: string;
  order?: string;
  date?: string;
}): Promise<{ items: ApiMatch[]; pagination: { page: number; limit: number; total: number } }> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.order) query.set("order", params.order);
  if (params?.date) query.set("date", params.date);

  const res = await fetch(`${API_URL}/api/v1/matches?${query}`, {
    cache: "no-store",
  });

  if (!res.ok) throw new Error("Erreur lors de la récupération des matchs");
  const json = await res.json();
  return json.data;
}

export async function fetchAnalyses(): Promise<ApiAnalysis[]> {
  const res = await fetch(`${API_URL}/api/v1/analyses`, {
    cache: "no-store",
  });

  if (!res.ok) throw new Error("Erreur lors de la récupération des analyses");
  const json = await res.json();
  return json.data;
}

export function riskLabel(level: "LOW" | "MEDIUM" | "HIGH" | null) {
  const map = { LOW: "faible", MEDIUM: "modéré", HIGH: "élevé" } as const;
  return level ? map[level] : "modéré";
}

export function riskColors(level: "LOW" | "MEDIUM" | "HIGH" | null) {
  const map = {
    LOW:    { border: "#4ade80", bg: "rgba(34,197,94,0.10)",   text: "#4ade80" },
    MEDIUM: { border: "#eab308", bg: "rgba(234,179,8,0.10)",   text: "#eab308" },
    HIGH:   { border: "#f87171", bg: "rgba(248,113,113,0.10)", text: "#f87171" },
  };
  return map[level ?? "MEDIUM"];
}

export function formatKickoff(iso: string) {
  return new Date(iso).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
