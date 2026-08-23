import type { AEOGEOReport, AIVisibilitySnapshot, AnalyticsSnapshot, ApiErrorPayload, AuthorityObservation, BacklinkSnapshot, CompetitorGapReport, ContentBrief, ContentTarget, CrawlComparison, DashboardResponse, LocalSEOSnapshot, OutreachSnapshot, ProviderStatusResponse, RankCheck, RankTrackingSnapshot, SEOAuditPage, SEOAuditResponse, SEOIntelligenceReport, SiteCrawl, SiteCrawlHistory, SystemStatus, TrackedKeyword, VisibilityPrompt, VisibilityReport, VisibilityRunPayload, VisibilityRunPreview, WorkspaceSummary } from "@/types/api";
import type { AnalyticsPage } from "@/types/api";

const DEFAULT_API_URL = "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code = "api_error",
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function apiBaseUrl(): string {
  return (process.env.NEXORA_API_BASE_URL || DEFAULT_API_URL).replace(/\/$/, "");
}

function requestUrl(path: string): string {
  if (typeof window !== "undefined" && path.startsWith("/api/v1/")) {
    return `/api/nexora/${path.slice("/api/v1/".length)}`;
  }
  return `${apiBaseUrl()}${path}`;
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit & { timeoutMs?: number } = {},
): Promise<T> {
  const { timeoutMs = 10_000, ...requestInit } = init;
  const timeoutController = new AbortController();
  const timeout = setTimeout(() => timeoutController.abort(), timeoutMs);
  const signal = requestInit.signal
    ? AbortSignal.any([requestInit.signal, timeoutController.signal])
    : timeoutController.signal;
  let response: Response;
  try {
    response = await fetch(requestUrl(path), {
      ...requestInit,
      signal,
      headers: { Accept: "application/json", ...requestInit.headers },
      cache: requestInit.cache ?? "no-store",
    });
  } finally {
    clearTimeout(timeout);
  }
  if (!response.ok) {
    let payload: ApiErrorPayload | undefined;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = undefined;
    }
    throw new ApiError(
      payload?.error.message || "The Nexora API request failed.",
      response.status,
      payload?.error.code,
      payload?.error.request_id,
    );
  }
  return (await response.json()) as T;
}

export function getSystemHealth(): Promise<SystemStatus> {
  return apiRequest<SystemStatus>("/api/v1/health", {
    next: { revalidate: 30 },
  });
}

export function getDashboard(): Promise<DashboardResponse> {
  return apiRequest<DashboardResponse>("/api/v1/dashboard");
}

export function getSEOAudits(page = 1, limit = 25): Promise<SEOAuditPage> {
  return apiRequest<SEOAuditPage>(`/api/v1/seo/audits?page=${page}&limit=${limit}`);
}

export function getSEOIntelligence(): Promise<SEOIntelligenceReport> {
  return apiRequest<SEOIntelligenceReport>("/api/v1/seo/intelligence");
}

export async function runSEOAudit(url: string): Promise<SEOAuditResponse> {
  const response = await fetch("/api/nexora/seo/audits", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ url }),
  });
  const payload = (await response.json()) as SEOAuditResponse | ApiErrorPayload;
  if (!response.ok && "error" in payload) {
    throw new ApiError(payload.error.message, response.status, payload.error.code, payload.error.request_id);
  }
  return payload as SEOAuditResponse;
}

export function getBacklinks(targetDomain?: string): Promise<BacklinkSnapshot> {
  const query = targetDomain ? `?target_domain=${encodeURIComponent(targetDomain)}` : "";
  return apiRequest<BacklinkSnapshot>(`/api/v1/backlinks${query}`);
}
async function backlinkAction<T>(path:string,init:RequestInit={}):Promise<T>{const response=await fetch(`/api/nexora/backlinks/${path}`,{...init,headers:{Accept:"application/json","Content-Type":"application/json",...init.headers}});const payload=await response.json() as T|ApiErrorPayload;if(!response.ok&&typeof payload==="object"&&payload!==null&&"error" in payload)throw new ApiError(payload.error.message,response.status,payload.error.code,payload.error.request_id);return payload as T}
export function previewAuthority(payload:{targets:string[];scope:string;force:boolean}):Promise<{preview:{requested:number;unique_targets:number;cached:number;provider_calls:number;maximum:number}}>{return backlinkAction("authority/preview",{method:"POST",body:JSON.stringify(payload)})}
export function enrichAuthority(payload:{targets:string[];scope:string;force:boolean}):Promise<AuthorityObservation[]>{return backlinkAction("authority/enrich",{method:"POST",body:JSON.stringify(payload)})}

export function getProviderStatus(): Promise<ProviderStatusResponse> {
  return apiRequest<ProviderStatusResponse>("/api/v1/settings/providers");
}

export function getWorkspaceSummary(workspace: string): Promise<WorkspaceSummary> {
  return apiRequest<WorkspaceSummary>(`/api/v1/workspaces/${encodeURIComponent(workspace)}`);
}

export function getRankTracking(): Promise<RankTrackingSnapshot> {
  return apiRequest<RankTrackingSnapshot>("/api/v1/rank-tracking");
}

async function rankAction<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/nexora/rank-tracking/${path}`, { ...init, headers: { Accept: "application/json", "Content-Type": "application/json", ...init.headers } });
  const payload = await response.json() as T | ApiErrorPayload;
  if (!response.ok && typeof payload === "object" && payload !== null && "error" in payload) {
    throw new ApiError(payload.error.message, response.status, payload.error.code, payload.error.request_id);
  }
  return payload as T;
}

export function addTrackedKeyword(payload: { keyword: string; target_domain: string; target_url?: string; country: string; device: string }): Promise<TrackedKeyword> {
  return rankAction<TrackedKeyword>("keywords", { method: "POST", body: JSON.stringify(payload) });
}

export function checkRanks(depth: number): Promise<{ checked: number; results: RankCheck[] }> {
  return rankAction("check", { method: "POST", body: JSON.stringify({ depth }) });
}

export function getRankHistory(keywordId: string): Promise<RankCheck[]> {
  return rankAction<RankCheck[]>(`keywords/${encodeURIComponent(keywordId)}/history`);
}

export function getSiteCrawls(options: { startUrl?: string; limit?: number; sortBy?: "completed_at" | "started_at" | "start_url"; descending?: boolean } = {}): Promise<SiteCrawlHistory> {
  const query = new URLSearchParams();
  if (options.startUrl) query.set("start_url", options.startUrl);
  if (options.limit) query.set("limit", String(options.limit));
  if (options.sortBy) query.set("sort_by", options.sortBy);
  if (options.descending !== undefined) query.set("descending", String(options.descending));
  const suffix = query.toString();
  return apiRequest(`/api/v1/site-crawl/runs${suffix ? `?${suffix}` : ""}`);
}
async function crawlAction<T>(path:string,init:RequestInit={}):Promise<T>{const response=await fetch(`/api/nexora/site-crawl/${path}`,{...init,headers:{Accept:"application/json","Content-Type":"application/json",...init.headers}});const payload=await response.json() as T|ApiErrorPayload;if(!response.ok&&typeof payload==="object"&&payload!==null&&"error" in payload)throw new ApiError(payload.error.message,response.status,payload.error.code,payload.error.request_id);return payload as T;}
export function startSiteCrawl(payload:{start_url:string;max_pages:number;max_depth:number;max_concurrency:number}):Promise<SiteCrawl>{return crawlAction("runs",{method:"POST",body:JSON.stringify(payload)});}
export function getSiteCrawlDetail(id:string):Promise<{crawl:SiteCrawl;comparison:CrawlComparison}>{return crawlAction(`runs/${encodeURIComponent(id)}`);}
export function getCompetitorTargets():Promise<string[]>{return apiRequest("/api/v1/competitor-gaps/targets")}
export function getCompetitorReport(target:string):Promise<CompetitorGapReport>{return apiRequest(`/api/v1/competitor-gaps/report?target_domain=${encodeURIComponent(target)}`)}
export function getContentTargets():Promise<ContentTarget[]>{return apiRequest("/api/v1/content/targets")}
export async function exportContentBrief(payload:{target_domain:string;keyword:string}):Promise<string>{const response=await fetch("/api/nexora/content/briefs/markdown",{method:"POST",headers:{Accept:"text/markdown","Content-Type":"application/json"},body:JSON.stringify(payload)});if(!response.ok)throw new ApiError("The content brief export failed.",response.status);return response.text()}
export function getAEOGEOTargets():Promise<string[]>{return apiRequest("/api/v1/aeo-geo/targets")}
async function analysisAction<T>(path:string,init:RequestInit={}):Promise<T>{const response=await fetch(`/api/nexora/analysis/${path}`,{...init,headers:{Accept:"application/json","Content-Type":"application/json",...init.headers}});const payload=await response.json() as T|ApiErrorPayload;if(!response.ok&&typeof payload==="object"&&payload!==null&&"error" in payload)throw new ApiError(payload.error.message,response.status,payload.error.code,payload.error.request_id);return payload as T}
export function generateContentBrief(target_domain:string,keyword:string):Promise<ContentBrief>{return analysisAction("content/briefs",{method:"POST",body:JSON.stringify({target_domain,keyword})})}
export function getAEOGEOReport(target:string):Promise<AEOGEOReport>{return analysisAction(`aeo-geo/report?target_domain=${encodeURIComponent(target)}`)}
export function getAEOGEOQuestions(target:string,query=""):Promise<Record<string,unknown>[]> { return apiRequest(`/api/v1/aeo-geo/questions?target_domain=${encodeURIComponent(target)}${query?`&query=${encodeURIComponent(query)}`:""}`); }
export async function exportAEOGEOReport(target:string):Promise<string>{const response=await fetch(`/api/nexora/aeo-geo/export?target_domain=${encodeURIComponent(target)}`,{headers:{Accept:"text/markdown"}});if(!response.ok)throw new ApiError("AEO/GEO export failed.",response.status);return response.text()}
export async function createAEOGEOBrief(target_domain:string,query:string):Promise<ContentBrief>{return apiRequest("/api/v1/aeo-geo/brief",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({target_domain,query})})}
export function getAIVisibility():Promise<AIVisibilitySnapshot>{return apiRequest("/api/v1/ai-visibility")}
export function getAIVisibilityHistory():Promise<Record<string,unknown>[]> { return apiRequest("/api/v1/ai-visibility/history"); }
export function getAISourceDomains(targetDomain=""):Promise<Record<string,unknown>[]> { return apiRequest(`/api/v1/ai-visibility/source-domains${targetDomain?`?target_domain=${encodeURIComponent(targetDomain)}`:""}`); }
export function getAICitationStability():Promise<Record<string,unknown>[]> { return apiRequest("/api/v1/ai-visibility/stability"); }
export function getAIPageIntelligence(targetDomain:string):Promise<Record<string,unknown>[]> { return apiRequest(`/api/v1/ai-visibility/page-intelligence?target_domain=${encodeURIComponent(targetDomain)}`); }
async function visibilityAction<T>(path:string,init:RequestInit={}):Promise<T>{const response=await fetch(`/api/nexora/ai-visibility/${path}`,{...init,headers:{Accept:"application/json","Content-Type":"application/json",...init.headers}});const payload=await response.json() as T|ApiErrorPayload;if(!response.ok&&typeof payload==="object"&&payload!==null&&"error" in payload)throw new ApiError(payload.error.message,response.status,payload.error.code,payload.error.request_id);return payload as T}
export function addVisibilityPrompt(text:string):Promise<VisibilityPrompt>{return visibilityAction("prompts",{method:"POST",body:JSON.stringify({text})})}
export function previewVisibilityRun(payload:VisibilityRunPayload):Promise<VisibilityRunPreview>{return visibilityAction("runs/preview",{method:"POST",body:JSON.stringify(payload)})}
export function executeVisibilityRun(payload:VisibilityRunPayload):Promise<{preview:VisibilityRunPreview;report:VisibilityReport}>{return visibilityAction("runs",{method:"POST",body:JSON.stringify(payload)})}
export function getOutreach():Promise<OutreachSnapshot>{return apiRequest("/api/v1/outreach")}
export function getOutreachResource(resource:string,page=1,limit=25):Promise<{items:Record<string,unknown>[];pagination:Record<string,unknown>}>{return apiRequest(`/api/v1/outreach/resources/${encodeURIComponent(resource)}?page=${page}&limit=${limit}`)}
async function outreachAction<T>(path:string,body?:unknown):Promise<T>{const response=await fetch(`/api/nexora/outreach/${path}`,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:body===undefined?undefined:JSON.stringify(body)});const payload=await response.json() as T|ApiErrorPayload;if(!response.ok&&typeof payload==="object"&&payload!==null&&"error" in payload)throw new ApiError(payload.error.message,response.status,payload.error.code,payload.error.request_id);return payload as T}
export const createOutreachCampaign=(body:unknown)=>outreachAction<Record<string,unknown>>("campaigns",body);export const createOutreachCandidate=(body:unknown)=>outreachAction<Record<string,unknown>>("candidates",body);export const prepareOutreachMessage=(body:unknown)=>outreachAction<Record<string,unknown>>("messages/prepare",body);export const sendOutreachMessage=(id:string,body:unknown)=>outreachAction<Record<string,unknown>>(`messages/${encodeURIComponent(id)}/send`,body);export const checkOutreachReplies=()=>outreachAction<Record<string,unknown>[]>("replies/check");
export function getLocalSEO():Promise<LocalSEOSnapshot>{return apiRequest("/api/v1/local-seo")};export async function refreshGBP(){const response=await fetch("/api/nexora/local-seo/gbp/refresh",{method:"POST",headers:{Accept:"application/json"}});const payload=await response.json() as Record<string,unknown>|ApiErrorPayload;if(!response.ok){const failure=payload as ApiErrorPayload;throw new ApiError(failure.error?.message||"GBP refresh failed.",response.status,failure.error?.code,failure.error?.request_id)}return payload}
export function getAnalytics():Promise<AnalyticsSnapshot>{return apiRequest("/api/v1/analytics")}
export function getAnalyticsResource(path:string,params:URLSearchParams):Promise<AnalyticsPage>{return apiRequest(`/api/v1/analytics/${path}?${params}`)}
export function refreshAnalytics(source:"gsc"|"ga4",payload:Record<string,string>):Promise<Record<string,unknown>>{return apiRequest(`/api/v1/analytics/refresh/${source}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)})}
export function getPaidMedia(platform:"google-ads"|"meta-ads"):Promise<Record<string,unknown>[]>{return apiRequest(`/api/v1/${platform}`)}
export async function importPaidMedia(platform:"google-ads"|"meta-ads",payload:unknown){const response=await fetch(`/api/nexora/paid-media/${platform}/import`,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(payload)});const result=await response.json() as Record<string,unknown>|ApiErrorPayload;if(!response.ok){const failure=result as ApiErrorPayload;throw new ApiError(failure.error?.message||"Import failed.",response.status,failure.error?.code,failure.error?.request_id)}return result}
