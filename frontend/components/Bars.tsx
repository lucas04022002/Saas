import type { Outcome, Probs } from "@/lib/types";
import { formatPctInt } from "@/lib/format";

export function Bars({ probs, favourite, home, away, dark = false }: { probs: Probs; favourite: Outcome | null; home: string; away: string; dark?: boolean }) {
  const rows: [Outcome, string][] = [["home", home], ["draw", "Nul"], ["away", away]];
  const line = dark ? "border-line-dark" : "border-line";
  const track = dark ? "bg-[#3a3a3c]" : "bg-[#e5e5ea]";
  return (
    <div className={`mt-6 border-b ${line}`}>
      {rows.map(([k, label]) => {
        const fav = k === favourite;
        const color = fav ? (dark ? "text-paper" : "text-ink") : "text-muted";
        const fill = fav ? (dark ? "bg-paper" : "bg-ink") : "bg-faint";
        return (
          <div key={k} className={`grid grid-cols-[90px_1fr_44px] md:grid-cols-[110px_1fr_48px] items-center gap-4 border-t ${line} py-3 text-[15px] font-semibold ${color}`}>
            <span>{label}</span>
            <span className={`relative block h-[2px] ${track}`}><span className={`absolute -top-px left-0 h-1 ${fill}`} style={{ width: `${probs[k] * 100}%` }} /></span>
            <span className="text-right tabular-nums">{formatPctInt(probs[k])}</span>
          </div>
        );
      })}
    </div>
  );
}
