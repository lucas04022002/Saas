import { NextRequest, NextResponse } from "next/server";

const PROTECTED = ["/dashboard", "/historique", "/signal", "/profil"];

export function middleware(req: NextRequest) {
  const token = req.cookies.get("rushplay_token")?.value;
  const { pathname } = req.nextUrl;

  const isProtected = PROTECTED.some((p) => pathname.startsWith(p));
  if (isProtected && !token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("redirect", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/historique/:path*", "/signal/:path*", "/profil/:path*"],
};
