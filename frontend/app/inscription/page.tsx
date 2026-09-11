import { AuthForm } from "@/components/AuthForm";
export default function Inscription() {
  return <section className="site py-16 md:py-24"><h1 className="h-section">Créer un compte.</h1><p className="mt-3 max-w-[48ch] text-[17px] text-muted">Gratuit. Le favori de chaque match, sans limite. Réservé aux 18 ans et plus.</p><AuthForm mode="signup" /></section>;
}
