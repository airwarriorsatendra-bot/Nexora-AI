import { NextRequest } from "next/server";
import { proxyRequest } from "@/lib/proxy";
const allowed = new Set(["authority/preview", "authority/enrich", "profile", "referring-domains", "authority", "prospects", "reclamation", "history"]);
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) { return proxyRequest(request, (await context.params).path, "backlinks", allowed); }
export const GET = proxy;
export const POST = proxy;
