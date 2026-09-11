import Link from "next/link";
import { api } from "@/lib/api";
export async function Footer() {
  let warning = "Les paris sportifs comportent des risques : endettement, dépendance… Appelez le 09 74 75 13 13 (appel non surtaxé).";
  try { warning = (await api.legal()).warning; } catch { /* API indisponible : texte de secours */ }
  const links = [["/matchs", "Matchs"], ["/bookmakers", "Bookmakers"], ["/track-record", "Track record"], ["/tarifs", "Tarifs"], ["/mentions-legales", "Mentions légales"], ["/cgu", "CGU"]];
  return (
    <footer className="bg-grey border-t border-line text-muted text-xs leading-relaxed">
      <div className="site py-10">
        <div className="mb-4 flex flex-wrap gap-x-7 gap-y-2 font-medium text-ink">{links.map(([h, l]) => <Link key={h} href={h}>{l}</Link>)}</div>
        <p>{warning} Interdit aux mineurs. RushPlay est un service d&apos;information indépendant, pas un opérateur de paris. Les cotes affichées sont relevées auprès des opérateurs agréés par l&apos;ANJ et peuvent avoir changé.</p>
      </div>
    </footer>
  );
}
