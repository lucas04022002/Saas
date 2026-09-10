"use client";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { MatchSummary } from "@/lib/types";
import { BOOK_LABELS } from "@/lib/types";
import { formatDateFr } from "@/lib/format";
const label = "block text-[12px] font-semibold uppercase tracking-[0.04em] text-muted";
const field = "mt-2 w-full border-0 border-b border-ink bg-transparent py-2 text-[17px] font-medium outline-none";
export function BetForm({ token, preselected, onSaved }: { token: string; preselected?: string; onSaved: () => void }) {
  const [matches, setMatches] = useState<MatchSummary[]>([]);
  const [f, setF] = useState({ match_id: preselected ?? "", outcome: "home", bookmaker: "betclic_fr", odds: "", stake: "" });
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.matches({ limit: 200 }, token).then((r) => { setMatches(r.items); setF((s) => ({ ...s, match_id: s.match_id || r.items[0]?.id || "" })); }).catch(() => setMatches([])); }, [token]);
  const m = matches.find((x) => x.id === f.match_id);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    try {
      await api.bankroll.create(token, { match_id: f.match_id, outcome: f.outcome, bookmaker: f.bookmaker, odds: Number(f.odds), stake: Number(f.stake) });
      setF((s) => ({ ...s, odds: "", stake: "" })); onSaved();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Impossible d'enregistrer. Réessaie."); }
  }
  return (
    <form onSubmit={submit} className="mt-12 grid items-end gap-4 border-t border-ink pt-6 md:grid-cols-[2fr_1fr_1fr_1fr_1fr_auto]">
      <div><label className={label} htmlFor="match">Match</label><select id="match" className={field} value={f.match_id} onChange={(e) => setF({ ...f, match_id: e.target.value })}>{matches.map((x) => <option key={x.id} value={x.id}>{x.home_team} – {x.away_team} · {formatDateFr(x.kickoff_at)}</option>)}</select></div>
      <div><label className={label} htmlFor="outcome">Pari</label><select id="outcome" className={field} value={f.outcome} onChange={(e) => setF({ ...f, outcome: e.target.value })}><option value="home">{m?.home_team ?? "Domicile"}</option><option value="draw">Nul</option><option value="away">{m?.away_team ?? "Extérieur"}</option></select></div>
      <div><label className={label} htmlFor="bookmaker">Bookmaker</label><select id="bookmaker" className={field} value={f.bookmaker} onChange={(e) => setF({ ...f, bookmaker: e.target.value })}>{Object.entries(BOOK_LABELS).filter(([k]) => k !== "pinnacle").map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
      <div><label className={label} htmlFor="odds">Cote</label><input id="odds" type="number" step="0.01" min="1.01" required className={field} value={f.odds} onChange={(e) => setF({ ...f, odds: e.target.value })} /></div>
      <div><label className={label} htmlFor="stake">Mise</label><input id="stake" type="number" step="1" min="1" required className={field} value={f.stake} onChange={(e) => setF({ ...f, stake: e.target.value })} /></div>
      <button type="submit" className="btn" disabled={!f.match_id}>Noter ce pari</button>
      {error && <p role="alert" className="md:col-span-6 text-[14px] font-medium">{error}</p>}
    </form>
  );
}
