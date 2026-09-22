import type { MetadataRoute } from "next";

const SITE = "https://rushplay.fr";

/** robots.txt — les pages publiques sont indexables, l'espace connecté et les relais d'API non. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/compte", "/carnet", "/api/", "/connexion", "/inscription"] }],
    sitemap: `${SITE}/sitemap.xml`,
  };
}
