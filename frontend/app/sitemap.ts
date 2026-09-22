import type { MetadataRoute } from "next";

const SITE = "https://rushplay.fr";

/** sitemap.xml — les pages publiques seulement. Les fiches de match changent chaque semaine et
 *  passent par la liste ; les pages du compte ne concernent que leur titulaire. */
export default function sitemap(): MetadataRoute.Sitemap {
  const maintenant = new Date();
  const pages: { path: string; changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"]; priority: number }[] = [
    { path: "/", changeFrequency: "daily", priority: 1 },
    { path: "/matchs", changeFrequency: "daily", priority: 0.9 },
    { path: "/bookmakers", changeFrequency: "daily", priority: 0.6 },
    { path: "/track-record", changeFrequency: "daily", priority: 0.7 },
    { path: "/tarifs", changeFrequency: "monthly", priority: 0.8 },
    { path: "/mentions-legales", changeFrequency: "yearly", priority: 0.1 },
    { path: "/cgu", changeFrequency: "yearly", priority: 0.1 },
  ];
  return pages.map((p) => ({ url: `${SITE}${p.path}`, lastModified: maintenant, changeFrequency: p.changeFrequency, priority: p.priority }));
}
