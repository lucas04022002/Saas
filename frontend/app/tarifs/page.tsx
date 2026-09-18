import Link from "next/link";
import { getUser, isPro } from "@/lib/session";
import { PRICE_MONTHLY, PLAN_NAMES } from "@/lib/pricing";
import { BillingButton } from "@/components/BillingButton";
export const dynamic = "force-dynamic";
const li = (t: string, off = false) => <li key={t} className={`border-t border-line py-3 text-[16px] ${off ? "text-faint-text" : ""}`}>{t}</li>;
export default async function Tarifs() {
  const user = await getUser();
  return (
    <section className="site py-14 md:py-20">
      <p className="eyebrow">Tarifs</p>
      <h1 className="h-section mt-3">Deux matchs par semaine,<br />gratuitement.</h1>
      <p className="mt-3 mb-12 max-w-[56ch] text-[19px] text-muted">Le compte gratuit ouvre deux matchs par semaine, entièrement : le favori, sa probabilité et le score exact le plus probable. L&apos;abonnement ouvre tous les matchs, et ce que le marché ne dit pas au premier regard.</p>
      <div className="grid border-t border-ink md:grid-cols-2">
        <div className="py-10 md:border-r md:border-line md:pr-10">
          <div className="font-tight text-[34px] font-extrabold tracking-[-0.04em]">{PLAN_NAMES.STARTER}</div>
          <div className="mt-4 font-tight text-[72px] font-extrabold leading-none tracking-[-0.06em]">0<span className="ml-1 text-[20px] font-medium tracking-normal text-muted">€</span></div>
          <ul className="mt-7 list-none p-0">{["Deux matchs par semaine, entièrement ouverts", "Le favori, sa probabilité et le score exact", "L'analyse en trois phrases", "La forme et les face-à-face", "Le track record public"].map((t) => li(t))}{["Les matchs au-delà de deux par semaine", "Les écarts entre bookmakers", "Le mouvement des cotes, relevé par relevé", "Le comparateur", "Le carnet"].map((t) => li(t, true))}</ul>
          {!user ? <Link href="/inscription" className="btn-ghost mt-7">Créer un compte</Link> : isPro(user) ? <span className="mt-7 block text-[14px] text-muted">Inclus dans ton offre.</span> : <span className="btn-ghost mt-7 opacity-60">Ton offre actuelle</span>}
        </div>
        <div className="py-10 md:pl-10">
          <div className="font-tight text-[34px] font-extrabold tracking-[-0.04em]">{PLAN_NAMES.PRO}</div>
          <div className="mt-4 font-tight text-[72px] font-extrabold leading-none tracking-[-0.06em]">{PRICE_MONTHLY}<span className="ml-1 text-[20px] font-medium tracking-normal text-muted">€ / mois</span></div>
          <ul className="mt-7 list-none p-0">{["Tous les matchs, sans quota", "Le favori, sa probabilité et le score exact", "Les écarts entre bookmakers, match par match", "Le mouvement des cotes, relevé par relevé", "Le comparateur des bookmakers français", "Le carnet, réglé automatiquement", "Sans engagement, résiliable en un clic"].map((t) => li(t))}</ul>
          {isPro(user) ? (
            <span className="btn mt-7 opacity-60">Ton offre actuelle</span>
          ) : user ? (
            <div className="mt-7"><BillingButton action="checkout" label="S'abonner" /></div>
          ) : (
            // Sans compte, on ne peut pas ouvrir de paiement : Stripe a besoin
            // de savoir à qui rattacher l'abonnement.
            <Link href="/inscription?abonnement=1" className="btn mt-7">Créer un compte et s&apos;abonner</Link>
          )}
          <p className="mt-4 text-[13px] text-muted">Réservé aux 18 ans et plus. RushPlay ne prend pas de paris et ne touche rien des bookmakers.</p>
        </div>
      </div>
    </section>
  );
}
