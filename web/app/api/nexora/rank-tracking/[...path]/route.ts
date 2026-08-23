import { NextRequest, NextResponse } from "next/server";

const API_URL = (process.env.NEXORA_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function forward(request: NextRequest, path: string[]) {
  if (path.some((part) => !/^[a-zA-Z0-9-]+$/.test(part))) return NextResponse.json({ error: { code: "VALIDATION_ERROR", message: "Invalid route.", request_id: "web" } }, { status: 400 });
  const body = request.method === "GET" ? undefined : await request.text();
  if (body && body.length > 8192) return NextResponse.json({ error: { code: "PAYLOAD_TOO_LARGE", message: "Request is too large.", request_id: "web" } }, { status: 413 });
  const response = await fetch(`${API_URL}/api/v1/rank-tracking/${path.join("/")}`, { method: request.method, headers: { Accept: "application/json", ...(body ? { "Content-Type": "application/json" } : {}) }, body, cache: "no-store", signal: AbortSignal.timeout(65_000) });
  return new NextResponse(await response.text(), { status: response.status, headers: { "Content-Type": "application/json" } });
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) { return forward(request, (await context.params).path); }
export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) { return forward(request, (await context.params).path); }
