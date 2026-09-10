import Link from "next/link";
export function Reserved({ dark = false, what = "aux abonnés" }: { dark?: boolean; what?: string }) {
  return (
    <Link href="/tarifs" className={`block border-t border-b py-6 ${dark ? "border-line-dark text-paper" : "border-line text-ink"}`}>
      <span className="text-[17px] font-semibold">Réservé {what} ›</span>
      <span className={`mt-1 block text-[14px] ${dark ? "text-faint" : "text-muted"}`}>Les écarts entre bookmakers, le mouvement des cotes et le comparateur.</span>
    </Link>
  );
}
