import { NextResponse } from "next/server";
import { api } from "@/lib/api";
import { errorEnvelope, requireToken } from "@/lib/route-utils";

export async function GET() {
  const token = await requireToken();
  if (token instanceof NextResponse) return token;
  try {
    const data = await api.matches({ limit: 200 }, token);
    return NextResponse.json({ success: true, message: "", data });
  } catch (e) {
    return errorEnvelope(e);
  }
}
