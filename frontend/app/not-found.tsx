import Link from "next/link";
export default function NotFound() {
  return <section className="site py-24"><h1 className="h-section">Cette page n&apos;existe pas.</h1><Link href="/matchs" className="link mt-6 inline-block text-[17px]">Voir les matchs ›</Link></section>;
}
