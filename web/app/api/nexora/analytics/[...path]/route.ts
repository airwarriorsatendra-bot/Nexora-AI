import { NextRequest } from "next/server";
import { proxyBaseRequest } from "@/lib/proxy";
export async function GET(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){const {path}=await params;return proxyBaseRequest(request,`analytics/${path.join("/")}`)}
