"use client";
import { useEffect, useRef } from "react";
export function Reveal({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  // Le rendu initial (serveur et hydratation client) montre toujours le contenu : brancher sur `typeof
  // window` ferait diverger le HTML serveur du premier rendu client (avertissement d'hydratation). L'état
  // masqué-puis-révélé est appliqué directement au DOM depuis l'effet, jamais via setState synchrone dedans.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const canAnimate = "IntersectionObserver" in window && !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (!canAnimate) return;
    // Déjà dans le viewport au montage (ancre en milieu de page, retour depuis une autre page, etc.) :
    // pas la peine de le masquer puis de le révéler aussitôt, ça ne ferait qu'un clignotement.
    if (el.getBoundingClientRect().top < window.innerHeight) return;
    el.classList.remove("opacity-100");
    el.classList.add("opacity-0");
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      el.classList.remove("opacity-0");
      el.classList.add("opacity-100");
      io.disconnect();
    }, { threshold: 0.15 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return <div ref={ref} className={`${className} opacity-100 transition-opacity duration-700`}>{children}</div>;
}
