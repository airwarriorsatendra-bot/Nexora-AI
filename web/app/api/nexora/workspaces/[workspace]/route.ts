import { NextRequest } from "next/server";
import { proxyBaseRequest } from "@/lib/proxy";
export async function GET(request: NextRequest, context: { params: Promise<{ workspace: string }> }) { return proxyBaseRequest(request, `workspaces/${encodeURIComponent((await context.params).workspace)}`); }