import {AnalyticsWorkspace} from "@/components/analytics-workspace";
import {getAnalytics} from "@/lib/api";
export default async function Page(){const data=await getAnalytics().catch(()=>null);return <div className="page module-page"><div className="page-heading"><div><span className="eyebrow">Measurement</span><h1>Marketing analytics</h1><p>Persisted Google Search Console and GA4 evidence with explicit source separation.</p></div></div>{data?<AnalyticsWorkspace data={data}/>:<div className="error-state" role="alert">Analytics data is unavailable.</div>}</div>}
