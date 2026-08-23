import { NextRequest, NextResponse } from "next/server";

const API_URL = (process.env.NEXORA_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export async function POST(request: NextRequest) {
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > 4096) {
    return NextResponse.json({ error: { code: "payload_too_large", message: "Request is too large.", request_id: "web" } }, { status: 413 });
  }
  const response = await fetch(`${API_URL}/api/v1/seo/audits`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body,
    cache: "no-store",
    signal: AbortSignal.timeout(60_000),
  });
  return new NextResponse(await response.text(), {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}
