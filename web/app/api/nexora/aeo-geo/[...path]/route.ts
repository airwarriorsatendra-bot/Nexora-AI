import { NextRequest } from "next/server";
import { proxyRequest } from "@/lib/proxy";
const allowed = new Set(["targets", "report", "pages", "questions", "entities", "sources", "recommendations", "history", "export", "brief"]);
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) { return proxyRequest(request, (await context.params).path, "aeo-geo", allowed); }
export const GET = proxy;