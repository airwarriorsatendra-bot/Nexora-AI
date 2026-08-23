import { SiteCrawlWorkspace } from "@/components/site-crawl-workspace";
import { getSiteCrawls } from "@/lib/api";

export default async function Page({ searchParams }: { searchParams: Promise<{ start_url?: string; sort_by?: "completed_at" | "started_at" | "start_url"; descending?: string }> }) {
  const params = await searchParams;
  const data = await getSiteCrawls({ startUrl: params.start_url, sortBy: params.sort_by ?? "completed_at", descending: params.descending === "true" }).catch(() => null);
  return <div className="page module-page"><div className="page-heading"><div><span className="eyebrow">SEO intelligence</span><h1>Site Crawl</h1><p>Bounded same-site technical and internal-link observations with persisted history.</p></div></div><form className="filter-row" method="get" aria-label="Crawl history filters"><label><span>Start URL</span><input name="start_url" defaultValue={params.start_url ?? ""} maxLength={2048} /></label><label><span>Sort by</span><select name="sort_by" defaultValue={params.sort_by ?? "completed_at"}><option value="completed_at">Completed</option><option value="started_at">Started</option><option value="start_url">Start URL</option></select></label><label><span>Order</span><select name="descending" defaultValue={params.descending === "true" ? "true" : "false"}><option value="false">Ascending</option><option value="true">Descending</option></select></label><button className="secondary-button" type="submit">Apply filters</button></form><SiteCrawlWorkspace initial={data}/></div>;
}
