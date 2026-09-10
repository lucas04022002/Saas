import { NextResponse } from "next/server";
import { api } from "@/lib/api";
import { errorEnvelope, originGuard, requireToken } from "@/lib/route-utils";

export async function DELETE(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const guard = originGuard(req);
  if (guard) return guard;
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
