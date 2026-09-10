import Link from "next/link";
import { COMPETITIONS } from "@/lib/types";
export function CompetitionFilter({ date, selected }: { date: string; selected?: string }) {
  const all = [["", "Tous"], ...Object.entries(COMPETITIONS)];
  return (
    <div className="flex gap-2 overflow-x-auto py-3">
      {all.map(([code, label]) => (
        <Link key={code} href={`/matchs?date=${date}${code ? `&competition=${code}` : ""}`} className={`flex-none rounded-full px-3 py-1.5 text-[12px] font-semibold ${(selected ?? "") === code ? "bg-ink text-paper" : "bg-paper text-ink"}`}>{label}</Link>
      ))}
    </div>
  );
}
