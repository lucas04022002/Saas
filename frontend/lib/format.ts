const nf1 = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const formatPct = (p: number) => `${Math.round(p * 100)} %`;
export const formatPctInt = (p: number) => `${Math.round(p * 100)}`;
export const formatOdds = (o: number) => nf2.format(o);
export const formatMargin = (m: number) => `${nf1.format(m * 100)} %`;
export const formatGap = (g: number) => `${g >= 0 ? "+" : "−"}${nf1.format(Math.abs(g) * 100)} %`;
export const formatSigned = (x: number, unit = "") => `${x >= 0 ? "+" : "−"}${nf1.format(Math.abs(x))}${unit}`;
export const formatEuro = (x: number) => `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(x)} €`;
export const formatDateFr = (iso: string) =>
  new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Paris" }).format(new Date(iso)).replace(" à ", ", ");
export const formatTimeFr = (iso: string) => new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Paris" }).format(new Date(iso));
export const formatDayShort = (iso: string) => new Intl.DateTimeFormat("fr-FR", { weekday: "short", day: "numeric", timeZone: "Europe/Paris" }).format(new Date(iso));
export const sinceHours = (iso: string, now = new Date()) => Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 3600000));
export const parisDate = (d = new Date()) => new Intl.DateTimeFormat("fr-CA", { timeZone: "Europe/Paris" }).format(d); // YYYY-MM-DD
