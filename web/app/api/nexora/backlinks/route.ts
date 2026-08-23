import { NextRequest } from "next/server";
import { proxyBaseRequest } from "@/lib/proxy";
export async function GET(request: NextRequest) { return proxyBaseRequest(request, "backlinks"); }