import { NextRequest, NextResponse } from "next/server";

const MAX_BODY_BYTES = 8192;
const UPSTREAM_TIMEOUT_MS = 60_000;

function errorResponse(code: string, message: string, status: number) {
  return NextResponse.json({ error: { code, message, request_id: "web" } }, { status });
}

async function readBody(request: NextRequest): Promise<string | undefined> {
  if (request.method === "GET" || request.method === "HEAD") return undefined;
  if (!request.body) return "";
  const reader = request.body.getReader();
  const decoder = new TextDecoder();
  let size = 0;
  let body = "";
  try {
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      size += chunk.value.byteLength;
      if (size > MAX_BODY_BYTES) {
        await reader.cancel();
        throw new Error("payload_too_large");
      }
      body += decoder.decode(chunk.value, { stream: true });
    }
    return body + decoder.decode();
  } finally {
    reader.releaseLock();
  }
}

export async function proxyRequest(
  request: NextRequest,
  path: string[],
  prefix: string,
  allowed: ReadonlySet<string>,
) {
  if (path.some((segment) => segment === "." || segment === "..") || !allowed.has(path.join("/"))) {
    return errorResponse("INVALID_PATH", "The requested route is not supported.", 400);
  }
  let body: string | undefined;
  try {
    body = await readBody(request);
  } catch (error) {
    if (error instanceof Error && error.message === "payload_too_large") {
      return errorResponse("PAYLOAD_TOO_LARGE", "Request is too large.", 413);
    }
    return errorResponse("INVALID_REQUEST", "The request body could not be read.", 400);
  }
  const base = (process.env.NEXORA_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  const target = new URL(`${base}/api/v1/${prefix}/${path.map(encodeURIComponent).join("/")}`);
  target.search = request.nextUrl.search;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
  try {
    const response = await fetch(target, {
      method: request.method,
      headers: { Accept: "application/json", ...(body !== undefined ? { "Content-Type": request.headers.get("content-type") || "application/json" } : {}) },
      body,
      cache: "no-store",
      signal: controller.signal,
    });
    return new NextResponse(response.body, { status: response.status, headers: { "Content-Type": response.headers.get("content-type") || "application/json" } });
  } catch {
    return errorResponse("UPSTREAM_UNAVAILABLE", "The Nexora API could not be reached.", 502);
  } finally {
    clearTimeout(timeout);
  }
}

export async function proxyBaseRequest(request: NextRequest, prefix: string) {
  const base = (process.env.NEXORA_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  const target = new URL(`${base}/api/v1/${prefix}`);
  target.search = request.nextUrl.search;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
  try {
    const response = await fetch(target, { method: request.method, headers: { Accept: "application/json" }, cache: "no-store", signal: controller.signal });
    return new NextResponse(response.body, { status: response.status, headers: { "Content-Type": response.headers.get("content-type") || "application/json" } });
  } catch {
    return errorResponse("UPSTREAM_UNAVAILABLE", "The Nexora API could not be reached.", 502);
  } finally {
    clearTimeout(timeout);
  }
}
