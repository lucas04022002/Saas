import type { Form, H2H } from "@/lib/types";
import { formatDayShort } from "@/lib/format";
export function FormTable({ form, h2h, home, away }: { form: { home: Form; away: Form }; h2h: H2H[]; home: string; away: string }) {
  const seq = (s: string) => s.split("").join(" ");
  const row = (name: string, f: Form, suffix: string) => <tr><td className="py-4 font-bold border-b border-line">{`${name} ${suffix}`}</td><td className="py-4 tracking-[0.12em] border-b border-line">{f.played ? seq(f.sequence) : "—"}</td><td className="py-4 text-right tabular-nums border-b border-line">{f.played ? `${f.goals_for} – ${f.goals_against}` : "—"}</td></tr>;
  return (
    <>
      <table className="mt-4 w-full border-collapse text-[16px]">
        <thead><tr><th className="border-b border-ink pb-3 text-left text-[12px] font-semibold uppercase tracking-[0.06em] text-muted">Équipe</th><th className="border-b border-ink pb-3 text-left text-[12px] font-semibold uppercase tracking-[0.06em] text-muted">5 derniers</th><th className="border-b border-ink pb-3 text-right text-[12px] font-semibold uppercase tracking-[0.06em] text-muted">Buts</th></tr></thead>
        <tbody>{row(home, form.home, "(domicile)")}{row(away, form.away, "(extérieur)")}</tbody>
      </table>
      {h2h.length > 0 && <p className="mt-4 text-[14px] text-muted">Face-à-face : {h2h.map((m) => `${m.home} ${m.score} ${m.away} (${formatDayShort(m.kickoff_at)})`).join(", ")}</p>}
    </>
  );
}
