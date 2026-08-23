import { NextRequest } from "next/server";
import { proxyRequest } from "@/lib/proxy";
const allowed = new Set(["prompts", "runs/preview", "runs", "history", "source-domains", "stability", "page-intelligence"]);
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) { return proxyRequest(request, (await context.params).path, "ai-visibility", allowed); }
export const GET = proxy;
export const POST = proxy;
