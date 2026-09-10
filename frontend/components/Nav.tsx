import Link from "next/link";
import { getUser } from "@/lib/session";
export async function Nav() {
  const user = await getUser();
  const links = [["/matchs", "Matchs"], ["/bookmakers", "Bookmakers"], ["/track-record", "Track record"], ["/tarifs", "Tarifs"]];
  return (
    <header className="bg-black text-paper sticky top-0 z-20">
      <div className="site flex h-[52px] items-center justify-between border-b border-line-dark">
        <Link href="/" className="font-tight text-[19px] font-extrabold tracking-[-0.04em]">RushPlay</Link>
        <nav className="flex items-center gap-5 md:gap-8 text-[12.5px] font-medium text-[#c7c7cc]">
          {links.map(([href, label]) => <Link key={href} href={href} className="hover:text-paper">{label}</Link>)}
          {user ? <Link href={user.subscription_plan === "STARTER" ? "/compte" : "/carnet"} className="text-paper">{user.first_name}</Link> : <Link href="/connexion" className="text-paper">Se connecter</Link>}
        </nav>
      </div>
    </header>
  );
}
