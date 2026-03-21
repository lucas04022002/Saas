import "@/app/globals.css";

import type { Metadata } from "next";

import { ThemeProvider } from "@/components/contexts/theme-provider";
import { jetbrainsMono, plusJakartaSans, spaceGrotesk } from "@/lib/fonts";

import { siteConfig } from "../config/site";

export const metadata: Metadata = {
  title: {
    default: siteConfig.name,
    template: `%s - ${siteConfig.name}`,
  },
  metadataBase: new URL(siteConfig.url),
  description: siteConfig.description,
  keywords: [
    "paris sportifs",
    "football analytics",
    "algorithme prédiction",
    "value bet",
    "cotes bookmakers",
    "Ligue 1",
    "Premier League",
  ],
  authors: [{ name: "RushPlay" }],
  creator: "rushplay",
  openGraph: {
    type: "website",
    locale: "fr_FR",
    url: siteConfig.url,
    title: siteConfig.name,
    description: siteConfig.description,
    siteName: siteConfig.name,
    images: [
      {
        url: siteConfig.ogImage,
        width: 1200,
        height: 630,
        alt: siteConfig.name,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: siteConfig.name,
    description: siteConfig.description,
    images: [siteConfig.ogImage],
    creator: "@rushplay",
  },
  icons: {
    icon: "/favicon.svg",
    apple: "/apple-touch-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" style={{ colorScheme: "dark" }} className="dark">
      <body
        className={`${plusJakartaSans.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable} font-[family-name:var(--font-body)] bg-background antialiased`}
      >
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
