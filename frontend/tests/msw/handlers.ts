import { http, HttpResponse } from "msw";
export const API = "http://localhost:8000";
export const legal = { warning: "Les paris sportifs comportent des risques : endettement, dépendance… Appelez le 09 74 75 13 13 (appel non surtaxé).", minimum_age: 18, positioning: "Nous ne prédisons pas. Nous vous montrons ce que le marché pense, et où il se contredit." };
export const plan = { amount_cents: 900, currency: "EUR", interval: "month", interval_count: 1, livemode: false };
export const handlers = [
  http.get(`${API}/api/v1/legal`, () => HttpResponse.json({ success: true, message: "", data: legal })),
  // Le tarif par défaut. Sans ce gestionnaire, les pages qui affichent un prix
  // tomberaient toutes sur le repli sans qu'aucun test ne le signale : elles
  // passeraient au vert en n'exerçant jamais la lecture du tarif réel.
  http.get(`${API}/api/v1/billing/plan`, () => HttpResponse.json({ success: true, message: "", data: plan })),
];
