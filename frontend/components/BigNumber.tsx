"use client";
import { useEffect, useRef, useState } from "react";

export function BigNumber({ value, suffix, className = "" }: { value: number; suffix?: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  // Le rendu initial (serveur et hydratation client) affiche toujours `value` : brancher sur
  // `typeof window` ferait diverger le HTML serveur du premier rendu client (avertissement d'hydratation).
  const [shown, setShown] = useState(value);
  useEffect(() => {
    const canAnimate = "IntersectionObserver" in window && !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (!canAnimate || !ref.current) return;
    const el = ref.current;
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      const start = performance.now();
      const tick = (t: number) => {
        const k = Math.min(1, (t - start) / 600);
        setShown(Math.round(value * (1 - Math.pow(1 - k, 3))));
        if (k < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, { threshold: 0.4 });
    io.observe(el);
    return () => io.disconnect();
  }, [value]);
  return (
    <span ref={ref} className={className} aria-label={`${value}${suffix ?? ""}`}>
      <span>{shown}</span>{suffix ? <sup className="align-top text-[0.28em] font-bold tracking-[-0.02em] relative top-[0.3em] ml-[0.02em]">{suffix}</sup> : null}
    </span>
  );
}
