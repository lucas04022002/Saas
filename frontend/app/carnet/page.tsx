import { redirect } from "next/navigation";
import { getUser } from "@/lib/session";
import { Bankroll } from "@/components/Bankroll";
export const dynamic = "force-dynamic";
export default async function Carnet({ searchParams }: { searchParams: Promise<{ match?: string }> }) {
  const [user, { match }] = [await getUser(), await searchParams];
  if (!user) redirect("/connexion");
  return <section className="bg-grey"><div className="site py-14 md:py-20"><Bankroll preselected={match} /></div></section>;
}
