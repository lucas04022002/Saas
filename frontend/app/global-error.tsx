"use client";
import { Inter, Inter_Tight } from "next/font/google";
import "./globals.css";

// Mêmes instances de police que le layout racine : `next/font` déduplique au build, et sans elles
// les variables --font-inter/--font-inter-tight ne sont pas posées sur <html> dans cet arbre de
// secours, qui retomberait sur la pile system-ui.
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const interTight = Inter_Tight({ subsets: ["latin"], variable: "--font-inter-tight", display: "swap", weight: ["500", "600", "700", "800", "900"] });

// global-error remplace tout le layout racine (Next.js l'exige quand l'erreur vient du layout lui-même) :
// il doit donc fournir son propre <html>/<body> et ne peut pas compter sur components/Footer (qui va
// chercher le texte légal en base) — le bandeau ANJ est donc recopié ici en dur, identique au texte de
// secours utilisé par Footer si l'API est indisponible.
export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="fr" className={`${inter.variable} ${interTight.variable}`}>
      <body className="min-h-screen flex flex-col bg-paper text-ink font-sans">
        <section className="site py-24">
          <h1 className="h-section">Le service ne répond pas.</h1>
          <p className="mt-3 text-[19px] text-muted">Réessaie dans un instant.</p>
          <button onClick={reset} className="btn mt-8">Réessayer</button>
          <p className="mt-16 text-xs leading-relaxed text-muted">
            Les paris sportifs comportent des risques : endettement, dépendance… Appelez le 09 74 75 13 13
            (appel non surtaxé). Interdit aux mineurs. RushPlay est un service d&apos;information
            indépendant, pas un opérateur de paris. Les cotes affichées sont relevées auprès des opérateurs
            agréés par l&apos;ANJ et peuvent avoir changé.
          </p>
        </section>
      </body>
    </html>
  );
}
