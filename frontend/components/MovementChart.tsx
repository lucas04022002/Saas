import type { Outcome, Probs } from "@/lib/types";
import { formatDayShort, formatPct } from "@/lib/format";
export function MovementChart({ history, favourite }: { history: { taken_at: string; reference: Probs }[]; favourite: Outcome }) {
  if (history.length < 2) return <p className="hair py-6 text-[15px] text-muted">Un seul relevé pour l&apos;instant : le mouvement apparaîtra au prochain.</p>;
  const ys = history.map((h) => h.reference[favourite]);
  const min = Math.min(...ys) - 0.02, max = Math.max(...ys) + 0.02;
  const pts = ys.map((y, i) => [ (i / (ys.length - 1)) * 520, 190 - ((y - min) / (max - min)) * 150 ] as const);
  const path = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const first = history[0], last = history[history.length - 1];
  return (
    <svg viewBox="0 0 520 200" className="mt-6 h-[200px] w-full" role="img" aria-label={`Probabilité du favori de ${formatPct(ys[0])} à ${formatPct(ys[ys.length - 1])}`}>
      <line x1="0" y1="199" x2="520" y2="199" className="stroke-line" />
      <polyline points={path} fill="none" className="stroke-ink" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="5" className="fill-ink" />
      <text x="0" y="186" fontSize="13" className="fill-muted">{formatDayShort(first.taken_at)} · {formatPct(ys[0])}</text>
      <text x="520" y={Math.max(14, pts[pts.length - 1][1] - 14)} fontSize="13" fontWeight="600" textAnchor="end" className="fill-ink">{formatDayShort(last.taken_at)} · {formatPct(ys[ys.length - 1])}</text>
    </svg>
  );
}
