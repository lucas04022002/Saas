import type { Outcome, Probs } from "@/lib/types";
import { formatPctInt } from "@/lib/format";

export type BarRow = { key: string; label: string; value: number; highlight?: boolean };

export function Bars({ rows, dark = false }: { rows: BarRow[]; dark?: boolean }) {
  const line = dark ? "border-line-dark" : "border-line";
  const track = dark ? "bg-track-dark" : "bg-track";
  return (
    <div className={`mt-6 border-b ${line}`}>
      {rows.map((r) => {
        const color = r.highlight ? (dark ? "text-paper" : "text-ink") : "text-muted";
        const fill = r.highlight ? (dark ? "bg-paper" : "bg-ink") : "bg-faint";
        return (
          <div key={r.key} className={`grid grid-cols-[90px_1fr_44px] md:grid-cols-[110px_1fr_48px] items-center gap-4 border-t ${line} py-3 text-[15px] font-semibold ${color}`}>
            <span>{r.label}</span>
            <span className={`relative block h-[2px] ${track}`}><span className={`absolute -top-px left-0 h-1 ${fill}`} style={{ width: `${r.value * 100}%` }} /></span>
            <span className="text-right tabular-nums">{formatPctInt(r.value)}</span>
          </div>
        );
      })}
    </div>
  );
}

// Construit les trois lignes 1N2 (domicile/nul/extérieur) attendues par la plupart des appelants.
export function outcomeRows(probs: Probs, favourite: Outcome | null, home: string, away: string): BarRow[] {
  const labels: [Outcome, string][] = [["home", home], ["draw", "Nul"], ["away", away]];
  return labels.map(([k, label]) => ({ key: k, label, value: probs[k], highlight: k === favourite }));
}
