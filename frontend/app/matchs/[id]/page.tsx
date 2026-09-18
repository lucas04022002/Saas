import Link from "next/link";
import { notFound } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { getToken } from "@/lib/session";
import { formatDateFr, formatGoals, formatPct, formatPctInt, formatSigned } from "@/lib/format";
import { COMPETITIONS } from "@/lib/types";
import { BigNumber } from "@/components/BigNumber";
import { Bars, outcomeRows } from "@/components/Bars";
import { Reserved } from "@/components/Reserved";
import { BookTable } from "@/components/BookTable";
import { MovementChart } from "@/components/MovementChart";
import { FormTable } from "@/components/FormTable";
import { UnlockMatch } from "@/components/UnlockMatch";

function splitAnalysis(text: string): [string, string] {
  const idx = text.indexOf(". ");
  if (idx === -1) return [text, ""];
  return [text.slice(0, idx + 1), text.slice(idx + 2)];
}

export default async function Match({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const token = await getToken();
  let m;
  try { m = await api.match(id, token); } catch (e) { if (e instanceof ApiError && e.status === 404) notFound(); throw e; }
  const fav = m.favourite;
  const mv = m.movement && fav ? m.movement[fav.outcome] : null;
  const [firstSentence, rest] = m.analysis ? splitAnalysis(m.analysis) : ["", ""];
  return (
    <section className="site py-14 md:py-20">
      <div className="text-[14px] text-muted"><Link href="/matchs">Matchs</Link> › {COMPETITIONS[m.competition] ?? m.league}</div>
      <h1 className="mt-4 font-tight text-[44px] md:text-[96px] font-extrabold leading-[0.95] tracking-[-0.06em]">{m.home_team} <span className="text-faint">– {m.away_team}</span></h1>
      <p className="mt-3 text-[16px] text-muted">{formatDateFr(m.kickoff_at)} · {fav ? (fav.source === "moyenne" ? "moyenne des bookmakers, Pinnacle absent" : "référence Pinnacle") : "pas encore de relevé"}{m.odds_taken_at ? ` · relevé de ${formatDateFr(m.odds_taken_at).split(", ")[1]}` : ""}</p>
      {m.result && <p className="mt-2 text-[16px] font-semibold">Terminé : {m.home_team} {m.result.home} – {m.result.away} {m.away_team}</p>}

      {/* Verrouille : le favori et le score sont masques par le serveur, et la
          page dit pourquoi au lieu de laisser croire a une absence de donnee. */}
      {m.locked ? <div className="mt-10"><UnlockMatch matchId={m.id} quota={m.quota} /></div> : null}

      <div className="mt-12 grid gap-12 md:grid-cols-2 md:gap-16">
        <div>
          {fav && m.reference ? (
            <>
              <div className="num-page"><BigNumber value={Number(formatPctInt(fav.prob))} suffix="%" /></div>
              <div className="mt-4 text-[20px] font-semibold">{fav.label} favori {mv !== null && <span className="text-muted font-medium">· {mv >= 0 ? "▲" : "▼"} {formatSigned(mv, " pts").slice(1)} depuis le premier relevé</span>}</div>
              <Bars rows={outcomeRows(m.reference, fav.outcome, m.home_team, m.away_team)} />
            </>
          ) : m.locked ? (
            <p className="text-[19px] text-muted">Le favori et sa probabilité s&apos;affichent une fois le match ouvert.</p>
          ) : (
            <p className="text-[19px] text-muted">Pas encore de relevé de cotes pour ce match.</p>
          )}
        </div>
        <div>
          {firstSentence && <p className="text-[20px] md:text-[22px] leading-snug tracking-[-0.01em]">{firstSentence}</p>}
          {rest && <p className="mt-4 text-[20px] md:text-[22px] leading-snug tracking-[-0.01em] text-muted">{rest}</p>}
          <Link href={`/carnet?match=${m.id}`} className="btn mt-9">Noter ce pari</Link>
        </div>
      </div>

      <div className="mt-20 grid gap-12 md:grid-cols-2 md:gap-16">
        <div>
          <h3 className="h-sub">Score le plus probable selon le marché</h3>
          {m.top_score ? (
            <>
              <div className="num-page mt-6"><BigNumber value={m.top_score.score} /></div>
              <p className="mt-3 max-w-[40ch] text-[15px] text-muted">Un score exact reste le pari le plus dur : même le plus probable ne dépasse pas {formatPct(m.top_score.probability)}.</p>
              {m.expected_goals && (
                <p className="mt-1 text-[13px] text-muted">
                  {m.expected_goals.source === "marché" ? "Total attendu par le marché" : "Total moyen de la ligue"} : {formatGoals(m.expected_goals.total)} buts
                </p>
              )}
            </>
          ) : m.locked ? (
            <p className="mt-6 text-[19px] text-muted">Le score exact s&apos;affiche une fois le match ouvert.</p>
          ) : (
            <p className="mt-6 text-[19px] text-muted">Pas encore assez de cotes pour estimer un score.</p>
          )}
        </div>
        <div>
          <h3 className="h-sub">Les 5 scores les plus probables</h3>
          {m.locked || !m.score_distribution ? <div className="mt-6"><Reserved what="aux abonnés, la distribution complète des scores" /></div> :
            <Bars rows={m.score_distribution.map((s) => ({ key: s.score, label: s.score, value: s.probability, highlight: s.score === m.top_score?.score }))} />}
        </div>
      </div>

      <div className="mt-20 grid gap-12 md:grid-cols-2 md:gap-16">
        <div>
          <h3 className="h-sub">Bookmakers</h3>
          {m.locked || !m.books ? <div className="mt-6"><Reserved /></div> : <BookTable books={m.books} reference_book={m.reference_book} favourite={fav?.outcome ?? null} />}
        </div>
        <div>
          <h3 className="h-sub">Mouvement</h3>
          {m.locked || !m.history ? <div className="mt-6"><Reserved what="aux abonnés, relevé par relevé" /></div> : fav ? <MovementChart history={m.history} favourite={fav.outcome} /> : null}
          <h3 className="h-sub mt-10">Forme</h3>
          <FormTable form={m.form} h2h={m.h2h} home={m.home_team} away={m.away_team} />
        </div>
      </div>
    </section>
  );
}
