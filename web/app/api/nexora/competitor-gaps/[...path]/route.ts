import { NextRequest } from "next/server";
import { proxyRequest } from "@/lib/proxy";
const allowed = new Set(["targets", "report", "competitors", "keyword-gaps", "page-gaps", "serp-detail", "history"]);
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) { return proxyRequest(request, (await context.params).path, "competitor-gaps", allowed); }
export const GET = proxy;