import Link from "next/link";
import { formatDayShort, parisDate } from "@/lib/format";
export function DayPicker({ selected, competition }: { selected: string; competition?: string }) {
  const days = Array.from({ length: 7 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() + i); return parisDate(d); });
  return (
    <div className="flex rounded-[10px] bg-segment p-[3px]">
      {days.map((d) => (
        <Link key={d} href={`/matchs?date=${d}${competition ? `&competition=${competition}` : ""}`} aria-current={d === selected ? "page" : undefined} className={`flex-1 rounded-lg py-1.5 text-center text-[12px] font-semibold capitalize ${d === selected ? "bg-segment-on text-ink shadow-sm" : "text-muted"}`}>{formatDayShort(`${d}T12:00:00Z`)}</Link>
      ))}
    </div>
  );
}
