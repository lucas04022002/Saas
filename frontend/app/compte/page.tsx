import Link from "next/link";
import { redirect } from "next/navigation";
import { getUser, isPro } from "@/lib/session";
import { PLAN_NAMES, PRICE_MONTHLY } from "@/lib/pricing";
import { LogoutButton } from "@/components/LogoutButton";
import { BillingButton } from "@/components/BillingButton";
export const dynamic = "force-dynamic";
export default async function Compte({ searchParams }: { searchParams: Promise<{ abonnement?: string; paiement?: string }> }) {
  const user = await getUser();
  if (!user) redirect("/connexion");
  const { abonnement, paiement } = await searchParams;
  return (
    <section className="site py-16 md:py-24">
      <h1 className="h-section">{user.first_name}.</h1>
      {/* Retour de Stripe. Le compte n'est PAS déclaré payant ici : cette page
          s'ouvre à la main. Seul le webhook signé fait foi, et il arrive parfois
          une seconde après la redirection — d'où la formulation prudente. */}
      {paiement === "ok" && !isPro(user) && (
        <p className="mt-4 max-w-[48ch] text-[17px] text-muted">
          Paiement reçu. Votre abonnement s&apos;active dans quelques secondes — rechargez la page
          si l&apos;offre ci-dessous n&apos;a pas encore changé.
        </p>
      )}
      {paiement === "ok" && isPro(user) && (
        <p className="mt-4 max-w-[48ch] text-[17px] text-muted">
          Votre abonnement est actif. Merci.
        </p>
      )}
      {abonnement === "1" && !isPro(user) && (
        <p className="mt-4 max-w-[48ch] text-[17px] text-muted">
          Tous les matchs, sans quota, pour {PRICE_MONTHLY} € par mois.
        </p>
      )}
      <dl className="mt-10 max-w-[520px] border-t border-ink text-[17px]">
        {[["E-mail", user.email], ["Offre", PLAN_NAMES[user.subscription_plan]]].map(([k, v]) => <div key={k} className="grid grid-cols-[140px_1fr] gap-4 border-b border-line py-4"><dt className="text-muted">{k}</dt><dd className="font-medium">{v}</dd></div>)}
      </dl>
      <div className="mt-8">
        {isPro(user) ? (
          <>
            {/* Les CGU promettent une résiliation « en un clic depuis la page
                Compte ». C'était un e-mail à écrire. Le portail de Stripe tient
                la promesse, et gère aussi le moyen de paiement et les factures. */}
            <BillingButton action="portal" label="Gérer mon abonnement" variant="btn-ghost" />
            <p className="mt-3 max-w-[48ch] text-[14px] text-muted">
              Résiliation, moyen de paiement et factures. Sans engagement : la résiliation prend
              effet à la fin de la période déjà payée.
            </p>
          </>
        ) : (
          <>
            <BillingButton action="checkout" label={`S'abonner — ${PRICE_MONTHLY} € / mois`} />
            <p className="mt-3 max-w-[48ch] text-[14px] text-muted">
              Paiement par carte, chez Stripe. Sans engagement, résiliable en un clic depuis cette
              page. <Link href="/tarifs" className="link">Ce que contient l&apos;offre ›</Link>
            </p>
          </>
        )}
      </div>
      <div><LogoutButton /></div>
    </section>
  );
}
