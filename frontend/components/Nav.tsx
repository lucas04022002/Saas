import Link from "next/link";
import { getUser } from "@/lib/session";
export async function Nav() {
  const user = await getUser();
  const links = [["/matchs", "Matchs"], ["/bookmakers", "Bookmakers"], ["/track-record", "Track record"], ["/tarifs", "Tarifs"]];
  return (
    <header className="bg-black text-paper sticky top-0 z-20">
      <div className="site flex h-[52px] items-center justify-between gap-3 border-b border-line-dark">
        <Link href="/" className="shrink-0 font-tight text-[19px] font-extrabold tracking-[-0.04em]">RushPlay</Link>
        <nav className="flex min-w-0 items-center gap-4 overflow-x-auto text-[12.5px] font-medium whitespace-nowrap text-nav-muted [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden md:gap-8">
          {links.map(([href, label]) => <Link key={href} href={href} className="shrink-0 hover:text-paper">{label}</Link>)}
          {user ? <Link href={user.subscription_plan === "STARTER" ? "/compte" : "/carnet"} className="shrink-0 text-paper">{user.first_name}</Link> : <Link href="/connexion" className="shrink-0 text-paper">Se connecter</Link>}
        </nav>
      </div>
    </header>
  );
}
