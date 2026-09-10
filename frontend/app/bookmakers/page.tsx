import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { getToken } from "@/lib/session";
import { formatDateFr, formatGap, formatMargin, formatOdds } from "@/lib/format";
import { Reserved } from "@/components/Reserved";
import type { BookRow } from "@/lib/types";
export const dynamic = "force-dynamic";
const th = (t: string, right = false) => <th scope="col" className={`border-b border-ink pb-3 text-[12px] font-semibold uppercase tracking-[0.06em] text-muted ${right ? "text-right" : "text-left"}`}>{t}</th>;
export default async function Bookmakers() {
  const token = await getToken();
  let rows: BookRow[] | null = null;
  try { rows = (await api.books(token)).items; } catch (e) { if (!(e instanceof ApiError && e.status === 403)) throw e; }
  return (
    <section className="site py-14 md:py-20">
      <p className="eyebrow">Bookmakers · 7 prochains jours</p>
      <h1 className="h-section mt-3">Qui paie le mieux.</h1>
      <p className="mt-3 mb-10 max-w-[60ch] text-[19px] text-muted">Pour chaque bookmaker français, l&apos;écart le plus favorable par rapport à la référence Pinnacle sur les matchs à venir, et sa marge moyenne. Un écart positif veut dire qu&apos;il paie plus que ce que le marché implique.</p>
      {rows === null ? <Reserved /> : rows.length === 0 ? <p className="hair py-10 text-[19px]">Aucun relevé de cotes pour les prochains jours.</p> : (
        <table className="w-full border-collapse text-[16px]">
          <thead><tr>{th("Bookmaker")}{th("Meilleur écart")}{th("Écart", true)}{th("Écarts ≥ 3 %", true)}{th("Marge moyenne", true)}{th("Matchs", true)}</tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.bookmaker}>
              <td className="border-b border-line py-5 font-tight text-[24px] font-bold tracking-[-0.03em]">{r.label}</td>
              <td className="border-b border-line py-5 text-[15px]">{r.best ? <><Link href={`/matchs/${r.best.match_id}`} className="block font-semibold">{r.best.home_team} – {r.best.away_team}</Link><span className="text-muted">{r.best.outcome === "home" ? r.best.home_team : r.best.outcome === "away" ? r.best.away_team : "Nul"}, {formatOdds(r.best.odds)} · {formatDateFr(r.best.kickoff_at)}</span></> : "—"}</td>
              <td className="border-b border-line py-5 text-right font-tight text-[40px] font-extrabold tracking-[-0.05em] leading-none">{r.best ? formatGap(r.best.gap).replace(/\s?%$/, "") : "—"}<span className="font-sans text-[13px] font-medium text-muted"> %</span></td>
              <td className="border-b border-line py-5 text-right tabular-nums">{r.gaps_above_threshold}</td>
              <td className="border-b border-line py-5 text-right tabular-nums">{r.avg_margin === null ? "—" : formatMargin(r.avg_margin)}</td>
              <td className="border-b border-line py-5 text-right tabular-nums">{r.matches}</td>
            </tr>
          ))}</tbody>
        </table>
      )}
      <p className="mt-6 max-w-[70ch] text-[13px] leading-relaxed text-muted">Les cotes changent. Un écart affiché à midi peut avoir disparu à 17 h. RushPlay n&apos;a aucun lien commercial avec les bookmakers cités.</p>
    </section>
  );
}
