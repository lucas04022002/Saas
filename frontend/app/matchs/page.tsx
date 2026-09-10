import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import { formatDateFr, formatTimeFr, parisDate } from "@/lib/format";
import { COMPETITIONS } from "@/lib/types";
import { DayPicker } from "@/components/DayPicker";
import { CompetitionFilter } from "@/components/CompetitionFilter";
import { MatchRow } from "@/components/MatchRow";

const ORDER = ["F1", "E0", "SP1", "D1", "I1", "CL"];

export default async function Matchs({ searchParams }: { searchParams: Promise<{ date?: string; competition?: string }> }) {
  const { date = parisDate(), competition } = await searchParams;
  const token = await getToken();
  const { items } = await api.matches({ date, competition, limit: 200 }, token);
  const latest = items.map((m) => m.odds_taken_at).filter(Boolean).sort().at(-1);
  const groups = ORDER.map((c) => [c, items.filter((m) => m.competition === c)] as const).filter(([, ms]) => ms.length);
  const day = formatDateFr(`${date}T12:00:00Z`).split(",")[0];
  const dayCap = day.charAt(0).toUpperCase() + day.slice(1);
  return (
    <section className="site py-14 md:py-20">
      <h1 className="h-section">Matchs.</h1>
      <p className="mt-2 mb-6 text-[15px] text-muted">{dayCap} · {items.length} match{items.length > 1 ? "s" : ""}{latest ? ` · relevé de ${formatTimeFr(latest)}` : ""}</p>
      <DayPicker selected={date} competition={competition} />
      <CompetitionFilter date={date} selected={competition} />
      {groups.length === 0 ? <p className="hair mt-6 py-10 text-[19px]">Aucun match ce jour-là pour cette compétition.</p> : groups.map(([code, ms]) => (
        <div key={code} className="mt-10">
          <h3 className="eyebrow mb-2">{COMPETITIONS[code]}</h3>
          <div className="border-b border-line">{ms.map((m) => <MatchRow key={m.id} match={m} />)}</div>
        </div>
      ))}
    </section>
  );
}
