"use client";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { clientApi } from "@/lib/client-api";
import type { BankrollSummary, Bet } from "@/lib/types";
import { BOOK_LABELS } from "@/lib/types";
import { formatDateFr, formatEuro, formatOdds, formatSigned, formatSignedInt } from "@/lib/format";
import { Kpi } from "./Kpi";
import { BetForm } from "./BetForm";
const STATUS: Record<Bet["status"], string> = { PENDING: "En attente", WON: "Gagné", LOST: "Perdu", VOID: "Annulé" };
export function Bankroll({ preselected }: { preselected?: string }) {
  const [data, setData] = useState<{ items: Bet[]; summary: BankrollSummary } | null>(null);
  const [error, setError] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const load = useCallback(() => clientApi.bankroll.list().then((d) => { setData(d); setError(false); }).catch(() => setError(true)), []);
  useEffect(() => { load(); }, [load]);
  async function runAction(fn: () => Promise<unknown>) {
    try { await fn(); setActionError(null); await load(); }
    catch (err) { setActionError(err instanceof ApiError ? err.message : "Impossible d'enregistrer. Réessaie."); }
  }
  if (error) return (
    <>
      <p role="alert" className="text-muted">Impossible de charger ton carnet. Réessaie dans un instant.</p>
      <button className="btn-ghost mt-4" onClick={load}>Réessayer</button>
    </>
  );
  if (!data) return <p className="text-muted">Chargement…</p>;
  const s = data.summary;
  const outcomeLabel = (b: Bet) => (b.outcome === "home" ? b.home_team : b.outcome === "away" ? b.away_team : "Nul");
  return (
    <>
      <p className="eyebrow">Carnet</p>
      <h1 className="h-section mt-3">Ton vrai bilan.</h1>
      <p className="mt-3 mb-10 max-w-[56ch] text-[19px] text-muted">Chaque pari que tu notes est réglé automatiquement au résultat. Pas de conseil de mise, juste ce que tu as engagé et ce que ça a rendu.</p>
      <div className="grid border-t border-ink md:grid-cols-4">
        <Kpi label="Engagé" value={String(Math.round(s.stakes))} unit="€" />
        <Kpi label="Réglé" value={String(Math.round(s.settled_stakes))} unit="€" />
        <Kpi label="Résultat" value={s.settled_stakes ? formatSignedInt(s.profit) : "—"} unit={s.settled_stakes ? "€" : undefined} />
        <Kpi label="Rendement" value={s.roi === null ? "—" : formatSigned(s.roi * 100)} unit={s.roi === null ? undefined : "%"} />
      </div>
      {actionError && <p role="alert" className="mt-6 text-[14px] font-medium">{actionError}</p>}
      {data.items.length === 0 ? <p className="hair mt-10 py-8 text-[19px]">Aucun pari noté. Le premier est en bas de page.</p> : (
        <table className="mt-12 w-full border-collapse text-[15px]">
          <caption className="sr-only">Carnet de paris</caption>
          <thead><tr>{["Match", "Pari", "Bookmaker", "Cote", "Mise", "Gain", "Statut", ""].map((h, i) => <th key={h + i} scope="col" className={`border-b border-ink pb-3 text-[12px] font-semibold uppercase tracking-[0.06em] text-muted ${i >= 3 ? "text-right" : "text-left"}`}>{h || <span className="sr-only">Actions</span>}</th>)}</tr></thead>
          <tbody>{data.items.map((b) => (
            <tr key={b.id}>
              <td className="border-b border-line py-4 font-semibold">{b.home_team} – {b.away_team}<span className="block text-[13px] font-normal text-muted">{formatDateFr(b.kickoff_at)}</span></td>
              <td className="border-b border-line py-4">{outcomeLabel(b)}</td>
              <td className="border-b border-line py-4">{BOOK_LABELS[b.bookmaker] ?? b.bookmaker}</td>
              <td className="border-b border-line py-4 text-right tabular-nums">{formatOdds(b.odds)}</td>
              <td className="border-b border-line py-4 text-right tabular-nums">{formatEuro(b.stake)}</td>
              <td className="border-b border-line py-4 text-right tabular-nums">{b.payout === null ? "—" : formatEuro(b.payout)}</td>
              <td className={`border-b border-line py-4 text-right text-[12px] font-semibold uppercase tracking-[0.04em] ${b.status === "PENDING" ? "text-link" : b.status === "WON" ? "text-ink" : "text-faint"}`}>{STATUS[b.status]}</td>
              <td className="border-b border-line py-4 text-right">{b.status === "PENDING" && (b.match_status === "POSTPONED"
                ? <button className="text-[13px] font-medium text-link underline underline-offset-4" onClick={() => runAction(() => clientApi.bankroll.void(b.id))}>Annuler</button>
                : <button className="text-[13px] font-medium text-link underline underline-offset-4" onClick={() => runAction(() => clientApi.bankroll.remove(b.id))}>Supprimer</button>)}</td>
            </tr>
          ))}</tbody>
        </table>
      )}
      <BetForm preselected={preselected} onSaved={load} />
    </>
  );
}
