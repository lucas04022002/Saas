import { siteConfig } from "@/config/site";

const COLUMNS = [
  {
    title: "Produit",
    links: [
      { text: "Dashboard", href: "/dashboard" },
      { text: "Historique", href: "/historique" },
      { text: "Tarifs", href: "/#pricing" },
    ],
  },
  {
    title: "Compagnie",
    links: [
      { text: "À propos", href: "#" },
      { text: "Contact", href: "#" },
      { text: "Aide", href: "#" },
    ],
  },
  {
    title: "Légal",
    links: [
      { text: "Confidentialité", href: siteConfig.url },
      { text: "Conditions d'utilisation", href: siteConfig.url },
    ],
  },
];

export default function FooterSection() {
  return (
    <footer className="bg-[#0b0e14] w-full border-t border-[#454933]/15">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-7xl mx-auto py-12 px-6">
        {/* Brand column */}
        <div className="space-y-4">
          <div
            className="text-xl font-bold text-[#c8f000]"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            RushPlay
          </div>
          <p className="text-sm text-slate-500 max-w-xs leading-relaxed">
            Le leader de l&apos;analyse algorithmique pour les parieurs
            exigeants.
          </p>
        </div>
        {/* Link columns */}
        {COLUMNS.map((col) => (
          <div key={col.title} className="flex flex-col gap-4">
            <h4
              className="text-white font-bold uppercase text-xs tracking-widest"
              style={{ fontFamily: "var(--font-heading, sans-serif)" }}
            >
              {col.title}
            </h4>
            {col.links.map((link) => (
              <a
                key={link.text}
                href={link.href}
                className="text-slate-500 hover:text-white transition-colors text-sm"
              >
                {link.text}
              </a>
            ))}
          </div>
        ))}
      </div>
      {/* Bottom bar */}
      <div className="max-w-7xl mx-auto px-6 py-6 border-t border-[#454933]/15 flex flex-col md:flex-row justify-between items-center gap-4">
        <p className="text-sm text-slate-500">
          © {new Date().getFullYear()} RushPlay. Tous droits réservés.
        </p>
        <div className="flex gap-6 text-xs text-slate-600">
          <span>Made for winners.</span>
          <span>Version 4.2.0</span>
        </div>
      </div>
    </footer>
  );
}
