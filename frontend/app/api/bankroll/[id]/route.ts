import { NextResponse } from "next/server";
import { api } from "@/lib/api";
import { errorEnvelope, requireToken } from "@/lib/route-utils";

export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const token = await requireToken();
  if (token instanceof NextResponse) return token;
  const { id } = await params;
  try {
    const data = await api.bankroll.remove(token, id);
    return NextResponse.json({ success: true, message: "", data });
  } catch (e) {
    return errorEnvelope(e);
  }
}
