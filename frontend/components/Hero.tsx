import Link from "next/link";
import type { MatchSummary } from "@/lib/types";
import { BigNumber } from "./BigNumber";
import { formatPctInt, formatTimeFr } from "@/lib/format";

export function Hero({ match }: { match: MatchSummary | null }) {
  const fav = match?.favourite ?? null;
  return (
    <section className="relative overflow-hidden bg-black text-paper text-center">
      <picture className="absolute inset-0">
        <source media="(max-width: 700px)" srcSet="/photos/stade-nuit-900.webp" />
        <img src="/photos/stade-nuit.webp" alt="" className="h-full w-full object-cover object-[center_40%]" loading="eager" fetchPriority="high" />
      </picture>
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,.72)_0%,rgba(0,0,0,.45)_45%,rgba(0,0,0,.85)_100%)]" />
      <div className="site relative py-24 md:py-36 min-h-[620px] md:min-h-[760px] flex flex-col items-center justify-center">
        {match && fav ? (
          <>
            <div className="text-[15px] font-medium text-photo-text">{match.home_team} – {match.away_team} · {formatTimeFr(match.kickoff_at)} · {fav.source === "moyenne" ? "moyenne des bookmakers" : "référence Pinnacle"}</div>
            <div className="num-hero mt-3 [text-shadow:0_10px_60px_rgba(0,0,0,.6)]"><BigNumber value={Number(formatPctInt(fav.prob))} suffix="%" /></div>
            <h1 className="mt-8 max-w-[22ch] text-[30px] md:text-[40px] font-bold leading-[1.08] tracking-[-0.035em]">{fav.label} favori. D&apos;après le marché, pas d&apos;après nous.</h1>
          </>
        ) : (
          <h1 className="max-w-[16ch] text-[44px] md:text-[64px] font-extrabold leading-[1.02] tracking-[-0.045em]">On ne prédit rien. On lit le marché.</h1>
        )}
        <p className="mt-4 max-w-[44ch] text-[17px] md:text-[18px] leading-relaxed text-photo-text">RushPlay lit les cotes des bookmakers français, retire leur marge et te montre la probabilité que le marché donne vraiment à chaque issue.</p>
        <div className="mt-7 flex flex-wrap justify-center gap-7 text-[17px] font-medium">
          <Link href="/matchs" className="text-link">Voir les matchs du jour ›</Link>
          <a href="#comment" className="text-link">Comment ça marche ›</a>
        </div>
      </div>
    </section>
  );
}
