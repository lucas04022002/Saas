import Link from "next/link";
import { COMPETITION_GROUPS } from "@/lib/types";

/**
 * Le filtre par compétition. Vingt pastilles sur une seule ligne défilante ne se
 * lisent plus : chaque groupe a sa ligne et son libellé, et « Tous » reste en
 * tête du premier. Sur mobile, chaque ligne défile indépendamment.
 */
export function CompetitionFilter({ date, selected }: { date: string; selected?: string }) {
  const current = selected ?? "";
  const pill = (code: string, label: string) => (
    <Link
      key={code}
      href={`/matchs?date=${date}${code ? `&competition=${code}` : ""}`}
      aria-current={current === code ? "page" : undefined}
      className={`flex-none rounded-full px-3 py-1.5 text-[12px] font-semibold ${current === code ? "bg-ink text-paper" : "bg-paper text-ink"}`}
    >
      {label}
    </Link>
  );
  return (
    <div className="flex flex-col gap-2 py-3">
      {COMPETITION_GROUPS.map(([group, entries], i) => (
        <div key={group} className="flex flex-col items-start gap-1 sm:flex-row sm:items-center sm:gap-2">
          <span className="shrink-0 text-[11px] font-medium uppercase leading-[1.3] tracking-[0.08em] text-muted sm:w-[128px]">{group}</span>
          <div className="flex w-full min-w-0 gap-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {i === 0 ? pill("", "Tous") : null}
            {entries.map(([code, label]) => pill(code, label))}
          </div>
        </div>
      ))}
    </div>
  );
}
