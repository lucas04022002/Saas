export const siteConfig = {
  name: "RushPlay",
  url: "https://rushplay.app",
  getStartedUrl: "https://rushplay.app",
  ogImage: "https://rushplay.app/og.jpg",
  description:
    "Radar d'opportunités football. Détection algorithmique des écarts entre probabilités réelles et cotes bookmakers.",
  links: {
    twitter: "https://twitter.com/rushplay",
    github: "https://github.com/rushplay",
    email: "mailto:contact@rushplay.app",
  },
  pricing: {
    starter: "/signup",
    pro: "/signup?plan=pro",
  },
};

export type SiteConfig = typeof siteConfig;
