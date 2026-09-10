"use client";
import { useEffect, useRef, useState } from "react";
export function Reveal({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const canAnimate = typeof window !== "undefined" && "IntersectionObserver" in window && !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const [on, setOn] = useState(!canAnimate);
  useEffect(() => {
    if (!canAnimate || !ref.current) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setOn(true); io.disconnect(); } }, { threshold: 0.15 });
    io.observe(ref.current);
    return () => io.disconnect();
  }, [canAnimate]);
  return <div ref={ref} className={`${className} transition-opacity duration-700 ${on ? "opacity-100" : "opacity-0"}`}>{children}</div>;
}
