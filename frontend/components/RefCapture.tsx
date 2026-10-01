"use client";
import { useEffect } from "react";
import { captureRef } from "@/lib/ref";

// Monté une fois dans le layout : lit `?ref=` à l'arrivée (voir lib/ref.ts). N'affiche rien.
export function RefCapture() {
  useEffect(() => {
    captureRef();
  }, []);
  return null;
}
