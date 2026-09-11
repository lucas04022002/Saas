"use client";
export default function Error({ reset }: { error: Error; reset: () => void }) {
  return <section className="site py-24"><h1 className="h-section">Le service ne répond pas.</h1><p className="mt-3 text-[19px] text-muted">Réessaie dans un instant.</p><button onClick={reset} className="btn mt-8">Réessayer</button></section>;
}
