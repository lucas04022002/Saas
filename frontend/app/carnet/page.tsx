import { redirect } from "next/navigation";
import { getToken, getUser } from "@/lib/session";
import { Bankroll } from "@/components/Bankroll";
export const dynamic = "force-dynamic";
export default async function Carnet({ searchParams }: { searchParams: Promise<{ match?: string }> }) {
  const [token, user, { match }] = [await getToken(), await getUser(), await searchParams];
  if (!token || !user) redirect("/connexion");
  return <section className="bg-grey"><div className="site py-14 md:py-20"><Bankroll token={token} preselected={match} /></div></section>;
}
