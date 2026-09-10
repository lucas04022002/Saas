import type { Book, MatchDetail, Outcome } from "@/lib/types";
import { formatGap, formatMargin, formatOdds } from "@/lib/format";
const cell = (b: Book, k: Outcome, fav: Outcome | null) => (
  <td className={`py-4 text-right tabular-nums border-b border-line ${k === fav ? "font-bold" : ""}`}>{formatOdds(b[k])}{k === fav && b.gaps[k] >= 0.03 ? <span className="ml-2 rounded-full bg-ink px-2 py-[1px] text-[12px] font-semibold text-paper">{formatGap(b.gaps[k])}</span> : null}</td>
);
export function BookTable({ books, reference_book, favourite }: { books: Book[]; reference_book: MatchDetail["reference_book"]; favourite: Outcome | null }) {
  return (
    <table className="mt-8 w-full border-collapse text-[16px]">
      <thead><tr>{["Book", "1", "N", "2", "Marge"].map((h, i) => <th key={h} className={`border-b border-ink pb-3 text-[12px] font-semibold uppercase tracking-[0.06em] text-muted ${i ? "text-right" : "text-left"}`}>{h}</th>)}</tr></thead>
      <tbody>
        {reference_book && <tr><td className="py-4 font-bold border-b border-line">{reference_book.label}</td>{(["home", "draw", "away"] as Outcome[]).map((k) => <td key={k} className="py-4 text-right tabular-nums border-b border-line">{formatOdds(reference_book[k])}</td>)}<td className="py-4 text-right tabular-nums border-b border-line">{formatMargin(reference_book.margin)}</td></tr>}
        {books.map((b) => <tr key={b.bookmaker}><td className="py-4 border-b border-line">{b.label}</td>{cell(b, "home", favourite)}{cell(b, "draw", favourite)}{cell(b, "away", favourite)}<td className="py-4 text-right tabular-nums border-b border-line">{formatMargin(b.margin)}</td></tr>)}
      </tbody>
    </table>
  );
}
