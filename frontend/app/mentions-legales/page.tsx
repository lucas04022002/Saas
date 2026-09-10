export const metadata = { robots: { index: false } };
export default function MentionsLegales() {
  return (
    <section className="site py-16 md:py-24 max-w-[760px]">
      <h1 className="h-section">Mentions légales.</h1>
      <p className="hair mt-8 py-5 text-[15px] text-muted">Texte à compléter par Lucas avant la mise en ligne.</p>
      {["Éditeur", "Hébergeur", "Données personnelles", "Jeu responsable"].map((t) => <div key={t} className="hair py-6"><h2 className="font-tight text-[24px] font-bold tracking-[-0.03em]">{t}</h2><p className="mt-2 text-[16px] text-muted">À compléter.</p></div>)}
    </section>
  );
}
