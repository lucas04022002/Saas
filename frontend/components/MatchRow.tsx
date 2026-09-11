import Link from "next/link";
import type { MatchSummary } from "@/lib/types";
import { BOOK_LABELS } from "@/lib/types";
import { formatGap, formatPctInt, formatTimeFr, sinceHours } from "@/lib/format";

export function MatchRow({ match }: { match: MatchSummary }) {
  const fav = match.favourite;
  const tight = !!fav && fav.prob < 0.45;
  const mv = match.movement && fav ? match.movement[fav.outcome] : null;
  const stale = match.odds_taken_at ? sinceHours(match.odds_taken_at) : null;
  const refLabel = fav ? (fav.source === "moyenne" ? "moyenne, Pinnacle absent" : "référence Pinnacle") : "pas encore de relevé";
  return (
    <Link href={`/matchs/${match.id}`} className="grid grid-cols-[1fr_auto] md:grid-cols-[1.6fr_1fr_1fr_1fr_auto] items-center gap-3 md:gap-6 border-t border-line py-5 md:py-6 hover:bg-grey/60 transition-colors">
      <div>
        <div className="h-teams">{match.home_team} – {match.away_team}</div>
        <div className="mt-1.5 text-[13.5px] text-muted">{match.league} · {formatTimeFr(match.kickoff_at)} · {refLabel}{stale !== null && stale >= 6 ? ` · relevé il y a ${stale} h` : ""}</div>
      </div>
      <div className="hidden md:block text-[14px] text-muted">
        {match.locked ? <><b className="block text-[15px] font-semibold text-ink">Réservé</b>écarts</> :
          match.best_gap ? <><b className="block text-[15px] font-semibold text-ink">{BOOK_LABELS[match.best_gap.bookmaker] ?? match.best_gap.bookmaker} {formatGap(match.best_gap.gap)}</b>meilleur écart</> :
          <><b className="block text-[15px] font-semibold text-ink">—</b>aucun écart</>}
      </div>
      <div className="hidden md:block text-[14px] text-muted">
        {mv === null ? <><b className="block text-[15px] font-semibold text-ink">—</b>stable</> :
          <><b className="block text-[15px] font-semibold text-ink">{mv >= 0 ? "▲" : "▼"} {Math.round(Math.abs(mv))} pts</b>depuis le premier relevé</>}
      </div>
      <div className="hidden md:block text-[14px] text-muted">
        {match.top_score ? <><b className="block text-[15px] font-semibold text-ink">{match.top_score.score}</b>score le plus probable</> :
          <><b className="block text-[15px] font-semibold text-ink">—</b>score le plus probable</>}
      </div>
      <div className={`num-row text-right min-w-[110px] md:min-w-[150px] ${tight || !fav ? "text-faint" : "text-ink"}`}>
        {fav ? formatPctInt(fav.prob) : "—"}
        <small className="mt-1.5 block font-sans text-[12px] font-medium tracking-normal text-muted">{fav ? (tight ? `${fav.label}, serré` : `${fav.label} favori`) : "pas encore de relevé"}</small>
      </div>
    </Link>
  );
}
