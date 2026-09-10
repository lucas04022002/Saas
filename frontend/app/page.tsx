import Link from "next/link";
import { api } from "@/lib/api";
import { getToken, getUser, isPro } from "@/lib/session";
import { parisDate } from "@/lib/format";
import { Hero } from "@/components/Hero";
import { MatchRow } from "@/components/MatchRow";
import { TrackTeaser } from "@/components/TrackTeaser";
import { Reveal } from "@/components/Reveal";

export default async function Home() {
  const [token, user] = [await getToken(), await getUser()];
  const { items } = await api.matches({ date: parisDate(), limit: 50 }, token);
  const withFav = items.filter((m) => m.favourite);
  const star = isPro(user)
    ? [...withFav].sort((a, b) => (b.best_gap?.gap ?? -1) - (a.best_gap?.gap ?? -1))[0] ?? null
    : withFav[0] ?? null;
  let track = null;
  try { track = (await api.trackRecord("F1")).items[0] ?? null; } catch { track = null; }

  return (
    <>
      <Hero match={star} />
      <section className="site py-20 md:py-24">
        <h2 className="h-section">Aujourd&apos;hui.</h2>
        <p className="mt-3 mb-10 max-w-[52ch] text-[19px] text-muted">Le favori de chaque match et sa probabilité, sans compte. Les écarts entre bookmakers et le mouvement des cotes, pour les abonnés.</p>
        {items.length === 0 ? <p className="hair py-10 text-[19px]">Aucun match aujourd&apos;hui. Reviens demain.</p> : (
          <div className="border-b border-line">{items.slice(0, 4).map((m) => <MatchRow key={m.id} match={m} />)}</div>
        )}
        <Link href="/matchs" className="link mt-7 inline-block text-[17px]">Tous les matchs du jour ›</Link>
      </section>
      <section id="comment" className="relative bg-black text-paper">
        {/* eslint-disable-next-line @next/next/no-img-element -- WebP local servi tel quel, pas de next/image (spec : <picture>/<img>) */}
        <img src="/photos/stade-jour.webp" alt="" className="absolute inset-0 h-full w-full object-cover opacity-[.14]" loading="lazy" />
        <Reveal className="site relative py-24 md:py-28">
          <h2 className="h-section text-[48px] md:text-[72px] max-w-[14ch]">On ne prédit rien.<br /><span className="text-muted">On lit le marché.</span></h2>
          <div className="mt-14 grid gap-8 md:grid-cols-3">
            {[["On relève.", "Les cotes 1N2 de Betclic, Winamax, Unibet, PMU, NetBet et Pinnacle, plusieurs fois par jour. Chaque relevé est conservé."],
              ["On retire la marge.", "Un bookmaker vend toujours plus de 100 %. Ce qui reste une fois sa marge retirée, c'est la probabilité que le marché donne à chaque issue."],
              ["On te montre.", "Le favori, les écarts entre bookmakers, le mouvement depuis le premier relevé. Aucun bonus, aucune magie. Toi, tu décides."]].map(([t, p]) => (
              <div key={t} className="hair-dark pt-7"><b className="block font-tight text-[24px] font-bold tracking-[-0.03em]">{t}</b><p className="mt-2.5 text-[16px] leading-relaxed text-faint-dark">{p}</p></div>
            ))}
          </div>
        </Reveal>
      </section>
      <TrackTeaser row={track} />
    </>
  );
}
