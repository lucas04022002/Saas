import { AuthForm } from "@/components/AuthForm";
export default function Connexion() {
  return <section className="site py-16 md:py-24"><h1 className="h-section">Se connecter.</h1><AuthForm mode="login" /></section>;
}
