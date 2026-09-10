import { cookies } from "next/headers";
import { NextResponse } from "next/server";
const NAME = "rp_token";
export async function POST(req: Request) {
  let body: { token?: string };
  try { body = (await req.json()) as { token?: string }; }
  catch { return NextResponse.json({ ok: false }, { status: 400 }); }
  const { token } = body;
  if (!token || typeof token !== "string") return NextResponse.json({ ok: false }, { status: 400 });
  (await cookies()).set(NAME, token, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: 60 * 60 * 24 * 7 });
  return NextResponse.json({ ok: true });
}
export async function DELETE() {
  (await cookies()).delete(NAME);
  return NextResponse.json({ ok: true });
}
