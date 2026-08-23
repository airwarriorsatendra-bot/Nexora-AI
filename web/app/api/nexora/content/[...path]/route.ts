import { NextRequest } from "next/server";
import { proxyRequest } from "@/lib/proxy";
const allowed = new Set(["targets", "targets/page", "history", "briefs", "briefs/markdown"]);
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) { return proxyRequest(request, (await context.params).path, "content", allowed); }
export const GET = proxy;
export const POST = proxy;