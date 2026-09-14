import type { Metadata } from "next";
import { Inter, Inter_Tight } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { THEME_SCRIPT } from "@/lib/theme";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const interTight = Inter_Tight({ subsets: ["latin"], variable: "--font-inter-tight", display: "swap", weight: ["500", "600", "700", "800", "900"] });

export const metadata: Metadata = {
  title: "RushPlay — On ne prédit rien. On lit le marché.",
  description: "Le favori de chaque match, sa vraie probabilité, et là où les bookmakers se contredisent.",
  icons: { icon: "/favicon.svg", apple: "/apple-touch-icon.png" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // suppressHydrationWarning : le script inline pose data-theme sur <html> avant l'hydratation,
    // React doit garder le DOM plutôt que sa propre sortie pour cet élément.
    <html lang="fr" className={`${inter.variable} ${interTight.variable}`} suppressHydrationWarning>
      <head>
        {/* Joué pendant l'analyse du HTML, avant la première peinture : aucun flash clair. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-screen flex flex-col">
        <Nav />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
