import Link from "next/link";
import type { TrackRow } from "@/lib/types";
import { BigNumber } from "./BigNumber";
import { COMPETITIONS } from "@/lib/types";
export function TrackTeaser({ row }: { row: TrackRow | null }) {
  if (!row) return null;
  return (
    <section className="bg-grey">
      <div className="site grid gap-10 py-20 md:grid-cols-2 md:items-center md:py-24">
        <div className="num-page md:text-[200px]"><BigNumber value={Math.round(row.favourite_rate * 100)} suffix="%" /></div>
        <p className="text-[20px] md:text-[22px] leading-snug">des favoris ont gagné cette saison en {COMPETITIONS[row.competition] ?? row.competition}. <span className="text-muted">C&apos;est le marché, pas nous. Un favori à 58 % perd ou fait nul quatre fois sur dix. <Link href="/track-record" className="text-link underline underline-offset-4">Le track record complet, match par match ›</Link></span></p>
      </div>
    </section>
  );
}
