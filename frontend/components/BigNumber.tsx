"use client";
import { useEffect, useRef, useState } from "react";

export function BigNumber({ value, suffix, className = "" }: { value: number | string; suffix?: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const numeric = typeof value === "number";
  // Le rendu initial (serveur et hydratation client) affiche toujours `value` : brancher sur
  // `typeof window` ferait diverger le HTML serveur du premier rendu client (avertissement d'hydratation).
  const [shown, setShown] = useState<number | string>(value);
  useEffect(() => {
    // Un score ("2-1") n'est pas une quantité qui compte progressivement : seule une valeur numérique
    // (pourcentage) s'anime, une chaîne s'affiche telle quelle (déjà affichée via l'état initial).
    const canAnimate = numeric && "IntersectionObserver" in window && !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (!canAnimate || !ref.current) return;
    const el = ref.current;
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      const start = performance.now();
      const tick = (t: number) => {
        const k = Math.min(1, (t - start) / 600);
        setShown(Math.round((value as number) * (1 - Math.pow(1 - k, 3))));
        if (k < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, { threshold: 0.4 });
    io.observe(el);
    return () => io.disconnect();
  }, [value, numeric]);
  // role="img" + aria-label expose la valeur finale comme un seul bloc de texte : sans ça, un lecteur
  // d'écran énoncerait chaque étape de l'animation de comptage (le texte du <span> change en direct), et
  // découperait "58" et "%" en deux fragments séparés par les deux éléments enfants.
  return (
    <span ref={ref} className={className} role="img" aria-label={`${value}${suffix ?? ""}`}>
      <span aria-hidden="true">{shown}</span>{suffix ? <sup aria-hidden="true" className="align-top text-[0.28em] font-bold tracking-[-0.02em] relative top-[0.3em] ml-[0.02em]">{suffix}</sup> : null}
    </span>
  );
}
