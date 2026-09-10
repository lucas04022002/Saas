import { NextResponse } from "next/server";
import { api } from "@/lib/api";
import { errorEnvelope, requireToken } from "@/lib/route-utils";

export async function GET() {
  const token = await requireToken();
  if (token instanceof NextResponse) return token;
  try {
    const data = await api.bankroll.list(token);
    return NextResponse.json({ success: true, message: "", data });
  } catch (e) {
    return errorEnvelope(e);
  }
}

export async function POST(req: Request) {
  const token = await requireToken();
  if (token instanceof NextResponse) return token;
  const body = await req.json();
  try {
    const data = await api.bankroll.create(token, body);
    return NextResponse.json({ success: true, message: "", data });
  } catch (e) {
    return errorEnvelope(e);
  }
}
