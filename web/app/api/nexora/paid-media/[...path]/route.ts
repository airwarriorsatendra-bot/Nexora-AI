import { NextRequest } from "next/server";
import { proxyRequest } from "@/lib/proxy";
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path;
  const prefix = path[0] === "google-ads" ? "google-ads" : "meta-ads";
  if (path.some((segment) => segment === "." || segment === "..") || path.length !== 2 || path[1] !== "import") {
    return proxyRequest(request, ["invalid"], prefix, new Set());
  }
  return proxyRequest(request, path.slice(1), prefix, new Set(["import"]));
}
export const POST = proxy;
