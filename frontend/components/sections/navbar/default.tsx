import { Menu } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";

import { Button } from "../../ui/button";
import { Sheet, SheetContent, SheetTrigger } from "../../ui/sheet";

interface NavbarProps {
  className?: string;
  activePath?: string;
}

export default function Navbar({ className, activePath = "/" }: NavbarProps) {
  const links = [
    { text: "Accueil", href: "/" },
    { text: "Dashboard", href: "/dashboard" },
    { text: "Historique", href: "/historique" },
    { text: "Tarifs", href: "/tarifs" },
    { text: "Profil", href: "/profil" },
  ];

  return (
    <header
      className={cn(
        "fixed top-0 z-50 w-full bg-[#10131a]/80 backdrop-blur-xl border-b border-[#454933]/20",
        className,
      )}
    >
      <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-6">
        {/* Logo */}
        <Link
          href="/"
          className="text-2xl font-black tracking-tighter text-[#c8f000]"
          style={{ fontFamily: "var(--font-heading, sans-serif)" }}
        >
          RushPlay
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-8">
          {links.map((link) => {
            const isActive = activePath === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm font-semibold transition-colors ${
                  isActive
                    ? "text-[#c8f000] border-b-2 border-[#c8f000] pb-1"
                    : "text-slate-400 hover:text-white"
                }`}
                style={{ fontFamily: "var(--font-heading, sans-serif)" }}
              >
                {link.text}
              </Link>
            );
          })}
        </nav>

        {/* Actions */}
        <div className="hidden md:flex items-center gap-4">
          <a
            href="/login"
            className="text-sm font-semibold text-slate-400 hover:text-white transition-colors"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Connexion
          </a>
          <a
            href="/register"
            className="bg-[#c8f000] text-[#2a3400] px-5 py-2 rounded-xl text-sm font-extrabold hover:brightness-110 transition-all"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            Commencer
          </a>
        </div>

        {/* Mobile menu */}
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="size-5" />
              <span className="sr-only">Menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="right">
            <nav className="grid gap-6 text-lg font-medium mt-8">
              <Link href="/" className="text-2xl font-black text-[#c8f000]">
                RushPlay
              </Link>
              {links.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className="text-slate-400 hover:text-white transition-colors"
                >
                  {link.text}
                </a>
              ))}
              <a
                href="/register"
                className="bg-[#c8f000] text-[#2a3400] px-5 py-2 rounded-xl font-extrabold text-center"
              >
                Commencer
              </a>
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}
