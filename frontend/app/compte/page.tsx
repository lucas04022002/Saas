import Link from "next/link";
import { redirect } from "next/navigation";
import { getUser, isPro } from "@/lib/session";
import { PLAN_NAMES } from "@/lib/pricing";
import { LogoutButton } from "@/components/LogoutButton";
export const dynamic = "force-dynamic";
export default async function Compte({ searchParams }: { searchParams: Promise<{ abonnement?: string }> }) {
  const user = await getUser();
  if (!user) redirect("/connexion");
  const { abonnement } = await searchParams;
  return (
    <section className="site py-16 md:py-24">
      <h1 className="h-section">{user.first_name}.</h1>
      {abonnement === "1" && !isPro(user) && <p className="mt-4 max-w-[48ch] text-[17px] text-muted">Le paiement arrive bientôt. Écris-nous à contact@rushplay.fr pour être prévenu.</p>}
      <dl className="mt-10 max-w-[520px] border-t border-ink text-[17px]">
        {[["E-mail", user.email], ["Offre", PLAN_NAMES[user.subscription_plan]]].map(([k, v]) => <div key={k} className="grid grid-cols-[140px_1fr] gap-4 border-b border-line py-4"><dt className="text-muted">{k}</dt><dd className="font-medium">{v}</dd></div>)}
      </dl>
      {!isPro(user) && <Link href="/tarifs" className="link mt-6 inline-block text-[17px]">Passer à la lecture complète ›</Link>}
      <p className="mt-6 max-w-[48ch] text-[14px] text-muted">Sans engagement. Pour résilier, écris-nous à contact@rushplay.fr, c&apos;est fait le jour même.</p>
      <div><LogoutButton /></div>
    </section>
  );
}
