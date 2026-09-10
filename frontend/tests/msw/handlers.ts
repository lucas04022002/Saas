import { http, HttpResponse } from "msw";
export const API = "http://localhost:8000";
export const legal = { warning: "Les paris sportifs comportent des risques : endettement, dépendance… Appelez le 09 74 75 13 13 (appel non surtaxé).", minimum_age: 18, positioning: "Nous ne prédisons pas. Nous vous montrons ce que le marché pense, et où il se contredit." };
export const handlers = [
  http.get(`${API}/api/v1/legal`, () => HttpResponse.json({ success: true, message: "", data: legal })),
];
