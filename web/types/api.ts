export type ServiceState = "ok" | "ready" | "not_ready";

export interface SystemStatus {
  status: ServiceState;
  service: string;
  version: string;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    request_id: string;
  };
}

export interface DashboardMetric {
  key: string;
  label: string;
  value: number | null;
  availability: "available" | "unavailable";
  description: string;
  source: string;
}

export interface ActivityItem {
  category: string;
  title: string;
  detail: string;
  observed_at: string | null;
}

export interface DashboardResponse {
  metrics: DashboardMetric[];
  recent_activity: ActivityItem[];
  attention_count: number;
}

export interface PageMetadata {
  page: number;
  limit: number;
  returned: number;
  has_more: boolean;
}

export interface SEOIssue {
  category: string;
  severity: string;
  code: string;
  description: string;
  recommendation: string;
  evidence: string;
}

export interface SEOAudit {
  audit_id: string;
  url: string;
  audited_at: string;
  overall_score: number;
  category_scores: Record<string, number>;
  issues: SEOIssue[];
  metrics: Record<string, string | number | boolean | null>;
}

export interface SEOAuditResponse {
  success: boolean;
  audit: SEOAudit | null;
  errors: string[];
  message: string;
}

export interface SEOAuditPage {
  items: SEOAudit[];
  pagination: PageMetadata;
}

export interface SEOOpportunity {
  opportunity_type: string;
  subject: string;
  subject_kind: "query" | "page";
  clicks: number;
  impressions: number;
  ctr: string | number;
  average_position: string | number;
  priority_score: number;
  recommendation: string;
  evidence: string[];
}

export interface SEOIntelligenceReport {
  query_opportunities: SEOOpportunity[];
  page_opportunities: SEOOpportunity[];
  gsc_ga4_insights: SEOOpportunity[];
  notes: string[];
}

export interface BacklinkRecord {
  backlink_id: string;
  source_url: string;
  target_url: string;
  source_domain: string;
  target_domain: string;
  anchor_text: string;
  status: string;
  last_seen: string;
}

export interface BacklinkProspect {
  prospect_id: string;
  domain: string;
  representative_url: string;
  opportunity_type: string;
  score: number;
  priority: string;
  reasons: string[];
  domain_authority: number | null;
}

export interface AuthorityObservation {
  observation_id: string;
  provider: string;
  target: string;
  domain_authority: number | null;
  page_authority: number | null;
  spam_score: number | null;
  observed_at: string;
}

export interface BacklinkSnapshot {
  backlinks: BacklinkRecord[];
  opportunities: unknown[];
  authority: AuthorityObservation[];
  prospects: BacklinkProspect[];
  referring_domains: Array<Record<string, string | number>>;
  prospect_history: BacklinkProspect[];
  intersect: Array<Record<string, unknown>>;
  competitor_gaps: Array<Record<string, unknown>>;
  anchors: Array<Record<string, unknown>>;
  reclamation: Array<Record<string, string>>;
  moz_configured: boolean;
}

export interface ProviderStatusResponse {
  authentication: "DEFERRED_TO_SAAS_FOUNDATION";
  providers: Array<{
    provider: string;
    status: "CONFIGURED" | "MISSING" | "OFFLINE_READY";
    detail: string;
  }>;
}

export interface WorkspaceSummary {
  workspace: string;
  metrics: DashboardMetric[];
  note: string;
}

export interface TrackingContext { country: string; language: string; device: "desktop" | "mobile"; search_engine: string; location: string | null; }
export interface TrackedKeyword { keyword_id: string; keyword: string; target_domain: string; target_url: string | null; context: TrackingContext; active: boolean; gsc_average_position: string | number | null; gsc_clicks: number | null; gsc_impressions: number | null; }
export interface SERPResult { position: number; title: string; url: string; domain: string; snippet: string; result_type: string; }
export interface RankCheck { check_id: string; keyword_id: string; keyword: string; context: TrackingContext; depth: number; provider: string; results: SERPResult[]; target_position: number | null; checked_at: string; source: string; }
export interface RankChange { change_type: string; previous_position: number | null; current_position: number | null; movement: number | null; }
export interface RankRow { keyword: TrackedKeyword; latest_check: RankCheck | null; change: RankChange | null; }
export interface CompetitorObservation { domain: string; keywords_observed: number; top_3_appearances: number; top_10_appearances: number; average_observed_position: string | number; best_observed_position: number; }
export interface RankTrackingSnapshot { configured: boolean; rows: RankRow[]; competitors: CompetitorObservation[]; }
export interface CrawlStatistics { pages_crawled:number; indexable_signals:number; broken_links:number; redirects:number; internal_links:number; no_crawled_inlinks:number; depth_four_plus:number; duplicate_titles:number; missing_meta:number; }
export interface CrawledPage { [key:string]:unknown; normalized_url:string; status_code:number|null; indexability:string; title:string; h1s:string[]; word_count:number; inlink_count:number; outlink_count:number; depth:number; canonical:string|null; issues:string[]; }
export interface CrawlIssue { [key:string]:unknown; code:string; category:string; severity:string; affected_url:string; evidence:string; recommendation:string; }
export interface InternalLink { [key:string]:unknown; source_url:string; target_url:string; anchor_text:string; nofollow:boolean; target_status:number|null; issue:string|null; }
export interface LinkOpportunity { [key:string]:unknown; priority:number; target_url:string; evidence:string[]; suggested_action:string; provenance:string[]; }
export interface SiteCrawl { crawl_id:string; request:{start_url:string;max_pages:number;max_depth:number;max_concurrency:number}; completed_at:string; pages:CrawledPage[]; links:InternalLink[]; issues:CrawlIssue[]; opportunities:LinkOpportunity[]; summary:{overall_score:number;category_scores:Record<string,number>;statistics:CrawlStatistics;disclaimer:string}; robots_txt_supported:boolean; }
export interface CrawlComparison { previous_crawl_id:string|null;new_pages:string[];missing_pages:string[];new_issues:string[];resolved_issues:string[];status_changes:string[];metadata_changes:string[];inlink_changes:string[];depth_changes:string[]; }
export interface SiteCrawlHistory { items:SiteCrawl[];latest:SiteCrawl|null; }
export interface CompetitorGapReport { target_domain:string; competitors:Array<{domain:string;keywords_observed:number;serp_appearances:number;top_3_appearances:number;top_10_appearances:number;average_observed_position:string|number;target_overlap:number}>; keyword_gaps:Array<{keyword:string;gap_type:string;priority:string;target_position_label:string;best_competitor:string;competitor_position:number;competitors_ahead:number;gsc_impressions:number|null;mapped_page:string|null;content_gap:string;score:{total:number};recommended_action:string;serp:Array<{position:number;domain:string;url:string;title:string;snippet:string;is_target:boolean}>}>; page_gaps:Array<Record<string,unknown>>; trends:Array<Record<string,unknown>>; notes:string[]; }
export interface ContentTarget { target_domain:string;keyword:string;mapped_page:string|null; }
export interface ContentBrief { target_url:string|null;mode:string;primary_query:string;primary_query_reason:string;priority:string;score:{total:number};gsc_impressions:number|null;tracked_position:number|null;competitors_ahead:number;intent:string;intent_evidence:string[];current_title:string|null;current_meta:string|null;current_h1:string|null;technical_issues:string[];supporting_queries:Array<Record<string,unknown>>;serp_competitors:Array<Record<string,unknown>>;internal_links:Array<Record<string,unknown>>;h2_sections:string[];suggested_h1:string;actions:string[];technical_preconditions:string[];aeo_opportunities:string[];geo_readiness:string[];limitations:string[]; }
export interface AEOGEOReport { target_domain:string;questions:Array<{query:string;question_type:string;mapped_page:string|null;impressions:number|null;tracked_serp_position:number|null;priority_score:number;evidence:string[];recommended_action:string}>;pages:Array<{url:string;aeo:{total:number};geo:{total:number};aeo_level:string;geo_level:string;faq_status:string;question_opportunities:number;structured_data_types:string[];observations:string[];technical_issues:string[];recommendations:string[]}>;notes:string[]; }
export interface VisibilityProvider { provider:string;model:string;classification:string;web_grounding_supported:boolean;citations_supported:boolean;source_urls_supported:boolean; }
export interface VisibilityPrompt { prompt_id:string;text:string;category:string;source:string;context:string;active:boolean; }
export interface VisibilityObservation { observation_id:string;run_id:string;prompt_id:string;prompt:string;category:string;provider:string;model:string;classification:string;state:string;response_text:string;brand_mention:{name:string;count:number;mention_order:number}|null;competitor_mentions:Array<{name:string;count:number;mention_order:number}>;citations:Array<{url:string;normalized_url:string;domain:string;title:string;index:number;is_target:boolean;competitor:string|null}>;citation_tracking_available:boolean;target_domain_cited:boolean|null;target_urls_cited:string[];observed_at:string; }
export interface AIVisibilitySnapshot { providers:VisibilityProvider[];prompts:VisibilityPrompt[];history:VisibilityObservation[]; }
export interface VisibilityRunPayload { brand_name:string;target_domain:string;prompt_ids:string[];provider_names:string[];repetitions:number;brand_aliases:string[];competitors:Record<string,string[]>; }
export interface VisibilityRunPreview { prompts:number;providers:number;repetitions:number;total_api_calls:number; }
export interface VisibilityReport { run:{run_id:string;brand_name:string;target_domain:string;providers:string[];prompt_count:number;repetitions:number;created_at:string;observations:VisibilityObservation[]};provider_summaries:Array<{provider:string;model:string;successful_observations:number;brand_mention_coverage:number;citation_coverage:number|null;citation_denominator:number;competitor_mentions:number;mention_stability:number;sample_size:number}>;brand_mention_coverage:number;citation_coverage:number|null;citation_denominator:number;competitors_observed:number;target_domain_citations:number;actions:string[];limitations:string[]; }
export interface OutreachSnapshot { prospects:Record<string,unknown>[];contacts:Record<string,unknown>[];campaigns:Record<string,unknown>[];sequences:Record<string,unknown>[];steps:Record<string,unknown>[];messages:Record<string,unknown>[];replies:Record<string,unknown>[];followups:Record<string,unknown>[];suppressions:Record<string,unknown>[];history:Record<string,unknown>[];analytics:{prospects:number;contacts:number;sent:number;failed:number;bounced:number;replies:number;positive_replies:number;negative_replies:number};gmail_configured:boolean;live_send_enabled:boolean;sender_email:string;reply_provider_configured:boolean;provider_name:string; }
export interface LocalSEOSnapshot { gbp_configured:boolean;data:{locations:Record<string,unknown>[];nap_evidence:Record<string,unknown>[];nap_assessments:Record<string,unknown>[];reviews:Record<string,unknown>[];review_summaries:Record<string,unknown>[];ranks:Record<string,unknown>[];queries:Record<string,unknown>[];landing_pages:Record<string,unknown>[];citations:Record<string,unknown>[];citation_targets:Record<string,unknown>[];competitors:Record<string,unknown>[];opportunities:Record<string,unknown>[];history:Record<string,unknown>[]}; }
export interface AnalyticsSnapshot { report:{kpis:Record<string,unknown>[];insights:Record<string,unknown>[];period:Record<string,unknown>}|null;gsc:Record<string,unknown>|null;ga4:Record<string,unknown>|null;history:Record<string,unknown>[];gsc_resources:{summary:Record<string,unknown>|null;queries:Record<string,unknown>[];pages:Record<string,unknown>[];history:Record<string,unknown>[]};ga4_resources:{summary:Record<string,unknown>[];traffic:Record<string,unknown>[];pages:Record<string,unknown>[];acquisition:Record<string,unknown>[];events:Record<string,unknown>[];devices:Record<string,unknown>[];countries:Record<string,unknown>[]}; }
export interface AnalyticsPage { items:Record<string,unknown>[];total:number;limit:number;offset:number;has_more:boolean }
