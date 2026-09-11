import Link from "next/link";
import { api } from "@/lib/api";
import { COMPETITIONS } from "@/lib/types";
import { BigNumber } from "@/components/BigNumber";
import { Kpi } from "@/components/Kpi";
export default async function TrackRecord({ searchParams }: { searchParams: Promise<{ competition?: string }> }) {
  const { competition } = await searchParams;
  const { items, note, n_scored, exact_score_rate, winner_rate_from_score, score_note } = await api.trackRecord();
  const sel = items.find((r) => r.competition === (competition ?? "F1")) ?? items[0] ?? null;
  return (
    <section className="bg-black text-paper">
      <div className="site py-16 md:py-24">
        <p className="eyebrow text-faint-dark">Track record · public</p>
        <h1 className="h-section mt-3">Le favori a-t-il raison&nbsp;?</h1>
        {sel === null ? <p className="hair-dark mt-8 py-8 text-[19px]">Pas encore de match terminé avec un relevé de cotes. Le track record commence au premier coup d&apos;envoi.</p> : (
          <div className="mt-4 grid gap-12 md:grid-cols-2 md:gap-16">
            <div>
              <div className="num-page"><BigNumber value={Math.round(sel.favourite_rate * 100)} suffix="%" /></div>
              <p className="mt-6 max-w-[40ch] text-[19px] leading-relaxed text-faint-dark">des favoris ont gagné en {COMPETITIONS[sel.competition] ?? sel.competition} cette saison, sur {sel.played} matchs. {note} Le favori affiché est celui du dernier relevé avant le coup d&apos;envoi, jamais recalculé après coup.</p>
            </div>
            <table className="w-full border-collapse text-[16px]">
              <caption className="sr-only">Track record par compétition</caption>
              <thead><tr>{["Compétition", "Matchs", "Favori gagnant", "Taux"].map((h, i) => <th key={h} scope="col" className={`border-b border-paper pb-3 text-[12px] font-semibold uppercase tracking-[0.06em] text-faint-dark ${i ? "text-right" : "text-left"}`}>{h}</th>)}</tr></thead>
              <tbody>{items.map((r) => (
                <tr key={r.competition} className={r.competition === sel.competition ? "font-bold" : ""}>
                  <td className="border-b border-line-dark py-4"><Link href={`/track-record?competition=${r.competition}`} className="link-dark">{COMPETITIONS[r.competition] ?? r.competition}</Link></td>
                  <td className="border-b border-line-dark py-4 text-right tabular-nums">{r.played}</td>
                  <td className="border-b border-line-dark py-4 text-right tabular-nums">{r.favourite_won}</td>
                  <td className="border-b border-line-dark py-4 text-right tabular-nums">{`${Math.round(r.favourite_rate * 100)} %`}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
        {typeof exact_score_rate === "number" && typeof winner_rate_from_score === "number" && (
          <div className="mt-16">
            <div className="grid border-t border-paper md:grid-cols-2">
              <Kpi dark label="Scores exacts touchés" value={String(Math.round(exact_score_rate * 100))} unit="%" />
              <Kpi dark label="Bons vainqueurs (score affiché)" value={String(Math.round(winner_rate_from_score * 100))} unit="%" />
            </div>
            <p className="mt-6 max-w-[40ch] text-[15px] text-faint-dark">{score_note} Mesuré sur {n_scored} matchs terminés.</p>
          </div>
        )}
      </div>
    </section>
  );
}
