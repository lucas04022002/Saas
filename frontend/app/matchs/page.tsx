import Link from "next/link";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import { formatDateFr, formatTimeFr, parisDate } from "@/lib/format";
import { COMPETITIONS, COMPETITION_ORDER } from "@/lib/types";
import { DayPicker } from "@/components/DayPicker";
import { CompetitionFilter } from "@/components/CompetitionFilter";
import { MatchRow } from "@/components/MatchRow";

// L'ordre des groupes est celui du catalogue : une liste locale finirait par oublier une compétition.
const ORDER = COMPETITION_ORDER;

export default async function Matchs({ searchParams }: { searchParams: Promise<{ date?: string; competition?: string }> }) {
  const { date = parisDate(), competition } = await searchParams;
  const token = await getToken();
  const { items, quota } = await api.matches({ date, competition, limit: 200 }, token);
  const latest = items.map((m) => m.odds_taken_at).filter(Boolean).sort().at(-1);
  const groups = ORDER.map((c) => [c, items.filter((m) => m.competition === c)] as const).filter(([, ms]) => ms.length);
  // Le sous-titre compte les matchs réellement affichés (groupés par compétition), pas `items.length` :
  // une compétition renvoyée par l'API mais absente de ORDER serait comptée sans jamais être montrée.
  const shown = groups.reduce((n, [, ms]) => n + ms.length, 0);
  // Un jour vide annonce le prochain jour joué (22/09/2026 : un mardi de trêve internationale, la page
  // disait « Aucun match » et le visiteur repartait sans savoir que la Ligue des Nations reprenait jeudi).
  const prochain = groups.length === 0 ? await api.matchesNext(date, competition).catch(() => null) : null;
  const day = formatDateFr(`${date}T12:00:00Z`).split(",")[0];
  const dayCap = day.charAt(0).toUpperCase() + day.slice(1);
  return (
    <section className="site py-14 md:py-20">
      <h1 className="h-section">Matchs.</h1>
      <p className="mt-2 text-[15px] text-muted">{dayCap} · {shown} match{shown > 1 ? "s" : ""}{latest ? ` · relevé de ${formatTimeFr(latest)}` : ""}</p>
      {/* Le compteur est posé AVANT la liste : on sait ce dont on dispose avant
          de choisir, pas après avoir cliqué. */}
      <p className="mt-1 mb-6 text-[15px]">
        {quota.plan === "ANONYMOUS" ? (
          <>
            <Link href="/inscription" className="underline underline-offset-4">Créez un compte gratuit</Link>
            <span className="text-muted"> pour ouvrir deux matchs par semaine.</span>
          </>
        ) : quota.plan === "PRO" ? (
          <span className="text-muted">Tous les matchs sont ouverts, sans quota.</span>
        ) : (quota.remaining ?? 0) > 0 ? (
          <span className="text-muted">
            Il vous reste {quota.remaining} match{(quota.remaining ?? 0) > 1 ? "s" : ""} à ouvrir cette semaine.
          </span>
        ) : (
          <>
            <span className="text-muted">Vos deux matchs de la semaine sont ouverts. </span>
            <Link href="/tarifs" className="underline underline-offset-4">Ouvrir tous les matchs</Link>
          </>
        )}
      </p>
      <DayPicker selected={date} competition={competition} />
      <CompetitionFilter date={date} selected={competition} />
      {groups.length === 0 ? (
        <div className="hair mt-6 py-10">
          <p className="text-[19px]">Aucun match ce jour-là pour cette compétition.</p>
          {prochain ? (
            <p className="mt-3 text-[16px] text-muted">
              <Link href={`/matchs?date=${prochain.date}${competition ? `&competition=${competition}` : ""}`} className="underline underline-offset-4 text-ink">
                Prochains matchs : {formatDateFr(`${prochain.date}T12:00:00Z`).split(",")[0]}
              </Link>
              {" — "}{prochain.count} match{prochain.count > 1 ? "s" : ""} ({prochain.competitions.map((c) => COMPETITIONS[c] ?? c).join(", ")})
            </p>
          ) : null}
        </div>
      ) : groups.map(([code, ms]) => (
        <div key={code} className="mt-10">
          <h3 className="eyebrow mb-2">{COMPETITIONS[code]}</h3>
          <div className="border-b border-line">{ms.map((m) => <MatchRow key={m.id} match={m} />)}</div>
        </div>
      ))}
    </section>
  );
}
