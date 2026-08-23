import { NextRequest } from "next/server";
import { proxyRequest } from "@/lib/proxy";
const allowed = new Set(["campaigns", "candidates", "messages", "messages/prepare", "replies", "replies/check", "resources", "resources/prospects", "resources/contacts", "resources/campaigns", "resources/sequences", "resources/messages", "resources/replies", "resources/history", "resources/suppression"]);
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) { const path = (await context.params).path; const valid = allowed.has(path.join("/")) || (path.length === 3 && path[0] === "messages" && path[2] === "send"); return proxyRequest(request, valid ? path : ["invalid"], "outreach", new Set([valid ? path.join("/") : "invalid"])); }
export const POST = proxy;
export const GET = proxy;
